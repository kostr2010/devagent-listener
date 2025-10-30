import fastapi
import enum
import redis.asyncio

from .actions.get import task_info_get
from .actions.set import task_info_set


class Action(enum.IntEnum):
    ACTION_GET = 0
    ACTION_SET = 1


async def handle_task_info(
    redis: redis.asyncio.Redis,
    action: int,
    payload: str | None,
) -> dict:
    """Work with the temporary task meta information that is stored on the server

    Args:
        redis (redis.asyncio.Redis): Redis connection to take task metadata from
        action (int): Action required by the endpoint. Can be one of the `Action` enum
        payload (str | None): Payload for the endpoint. Interpreted differently depending on the action

    Raises:
        fastapi.HTTPException: in case of internal server errors

    Returns:
        dict: answer, depends on the action
    """

    _validate_action(action)

    if Action.ACTION_GET.value == action:
        return await task_info_get(payload, redis)

    if Action.ACTION_SET.value == action:
        # FIXME: lift this when adequate auth is added to the requests
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[handle_task_info] Can not invoke action={action} via url request",
        )
        return await task_info_set(payload, redis)

    raise fastapi.HTTPException(
        status_code=500,
        detail=f"[handle_task_info] Unhandled action={action}",
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
