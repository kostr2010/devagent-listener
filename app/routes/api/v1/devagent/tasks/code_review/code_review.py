import fastapi
import enum
import typing

from app.redis.async_redis import AsyncRedis
from app.db.async_db import AsyncDBSession
from app.diff.provider import DiffProvider

from app.routes.api.v1.devagent.tasks.code_review.actions.get import (
    action_get,
    Response as GetResponse,
)
from app.routes.api.v1.devagent.tasks.code_review.actions.run import (
    action_run,
    Response as RunResponse,
)
from app.routes.api.v1.devagent.tasks.code_review.actions.revoke import (
    action_revoke,
    Response as RevokeResponse,
)


class Action(enum.IntEnum):
    ACTION_GET = 0
    ACTION_RUN = 1
    ACTION_REVOKE = 2


Response = GetResponse | RunResponse | RevokeResponse


async def code_review(
    db: AsyncDBSession,
    redis: AsyncRedis,
    diff_provider: DiffProvider,
    action: int,
    query_params: dict[str, typing.Any],
) -> Response:
    """Work with the code review of the devagent for given PRs

    Args:
        db (AsyncSession): Database connection for persistent storage
        redis (AsyncRedis): Redis connection to take task metadata from
        action (int): Action required by the endpoint. Can be one of the `Action` enum
        query_params (dict): Payload for the endpoint. Interpreted differently depending on the action

    Raises:
        fastapi.HTTPException: in case of internal server errors or invalid user inputs

    Returns:
        Response: answer, depends on the action
    """

    _validate_action(action)

    if Action.ACTION_GET.value == action:
        return action_get(query_params=query_params)

    if Action.ACTION_RUN.value == action:
        return await action_run(
            db=db, redis=redis, diff_provider=diff_provider, query_params=query_params
        )

    if Action.ACTION_REVOKE.value == action:
        return action_revoke(query_params=query_params)

    raise fastapi.HTTPException(
        status_code=500,
        detail=f"[code_review] Unhandled action={action}",
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
