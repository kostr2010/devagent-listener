import enum
import fastapi
import typing

from app.redis.async_redis import AsyncRedis
from app.db.async_db import AsyncDBSession

from app.routes.api.v1.devagent.tasks.user_feedback.actions.get import (
    action_get,
    Response as GetResponse,
)
from app.routes.api.v1.devagent.tasks.user_feedback.actions.set import (
    action_set,
    Response as SetResponse,
)
from app.routes.api.v1.devagent.tasks.user_feedback.actions.update import (
    action_update,
    Response as UpdateResponse,
)


class Action(enum.IntEnum):
    ACTION_GET = 0
    ACTION_SET = 1
    ACTION_UPDATE = 2


Response = GetResponse | SetResponse | UpdateResponse


async def user_feedback(
    db: AsyncDBSession,
    redis: AsyncRedis,
    action: int,
    query_params: dict[str, typing.Any],
) -> Response:
    """Receive user feedback for the devagent alarm and record it in persistent storage

    Args:
        db (AsyncSession): Database connection for persistent storage
        redis (AsyncRedis): Redis connection to take task metadata from
        action (int): Action required by the endpoint. Can be one of the `Action` enum
        query_params (dict): Payload for the endpoint. Interpreted differently depending on the action

    Raises:
        fastapi.HTTPException: in case of internal server errors

    Returns:
        dict: answer, depends on the action
    """

    _validate_action(action)

    if Action.ACTION_GET.value == action:
        return await action_get(db=db, query_params=query_params)

    if Action.ACTION_SET.value == action:
        return await action_set(db=db, redis=redis, query_params=query_params)

    if Action.ACTION_UPDATE.value == action:
        return await action_update(db=db, query_params=query_params)

    raise fastapi.HTTPException(
        status_code=500,
        detail=f"[task_task_info] Unhandled action={action}",
    )


###########
# private #
###########


def _validate_action(action: int) -> None:
    if action not in [e.value for e in Action]:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid action value: action={action}",
        )
