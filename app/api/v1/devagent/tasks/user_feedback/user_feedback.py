import enum
import fastapi
import redis.asyncio
import sqlalchemy.ext.asyncio

from .actions.set import user_feedback_set


class Action(enum.IntEnum):
    ACTION_SET = 1


async def handle_user_feedback(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    action: int,
    query_params: dict,
) -> dict:
    """Receive user feedback for the devagent alarm and record it in persistent storage

    Args:
        postgres (sqlalchemy.ext.asyncio.AsyncSession): Postgres connection for persistent storage
        redis (redis.asyncio.Redis): Redis connection to take task metadata from
        action (int): Action required by the endpoint. Can be one of the `Action` enum
        query_params (dict): Payload for the endpoint. Interpreted differently depending on the action

    Raises:
        fastapi.HTTPException: in case of internal server errors

    Returns:
        dict: answer, depends on the action
    """

    _validate_action(action)

    if Action.ACTION_SET.value == action:
        return await user_feedback_set(
            postgres=postgres, redis=redis, query_params=query_params
        )

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
