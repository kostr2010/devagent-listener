import fastapi
import enum
import sqlalchemy.ext.asyncio
import redis.asyncio

from .actions.run import handle_code_review_run
from .actions.get import handle_code_review_get


class Action(enum.IntEnum):
    ACTION_GET = 0
    ACTION_RUN = 1


def handle_code_review(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    action: int,
    payload: str | None,
):
    _validate_action(action)

    if Action.ACTION_GET.value == action:
        return handle_code_review_get(payload)

    if Action.ACTION_RUN.value == action:
        return handle_code_review_run(postgres=postgres, redis=redis, payload=payload)

    raise fastapi.HTTPException(
        status_code=500,
        detail=f"[handle_code_review] Unhandled action={action}",
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
