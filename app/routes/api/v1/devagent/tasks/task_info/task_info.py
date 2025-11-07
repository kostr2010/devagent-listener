import fastapi
import enum
import redis.asyncio
import typing

from app.routes.api.v1.devagent.tasks.task_info.actions.get import (
    action_get,
    Response as GetResponse,
)
from app.routes.api.v1.devagent.tasks.task_info.actions.set import (
    action_set,
    Response as SetResponse,
)


class Action(enum.IntEnum):
    ACTION_GET = 0
    ACTION_SET = 1


Response = GetResponse | SetResponse


async def task_task_info(
    redis: redis.asyncio.Redis,
    action: int,
    query_params: dict[str, typing.Any],
) -> Response:
    """Work with the temporary task meta information that is stored on the server

    Args:
        redis (redis.asyncio.Redis): Redis connection to take task metadata from
        action (int): Action required by the endpoint. Can be one of the `Action` enum
        query_params (dict): Payload for the endpoint. Interpreted differently depending on the action

    Raises:
        fastapi.HTTPException: in case of internal server errors

    Returns:
        Response: answer, depends on the action
    """

    _validate_action(action)

    if Action.ACTION_GET.value == action:
        return await action_get(redis=redis, query_params=query_params)

    if Action.ACTION_SET.value == action:
        # TODO: lift this when adequate auth is added to the requests
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"[task_task_info] Can not invoke action={action} via url request",
        )
        return await action_set(redis=redis, query_params=query_params)  # type: ignore

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
