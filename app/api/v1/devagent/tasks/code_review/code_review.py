import fastapi
import enum
import sqlalchemy.ext.asyncio
import redis.asyncio

from .actions.run.run import handle_code_review_run
from .actions.get.get import handle_code_review_get


class Action(enum.IntEnum):
    ACTION_GET = 0
    ACTION_RUN = 1


def handle_code_review(action: int, payload: str | None) -> dict:
    """Work with the code review of the devagent for given PRs

    Args:
        action (int): Action required by the endpoint. Can be one of the `Action` enum
        payload (str | None): Payload for the endpoint. Interpreted differently depending on the action

    Raises:
        fastapi.HTTPException: in case of internal server errors

    Returns:
        dict: answer, depends on the action
    """

    _validate_action(action)

    if Action.ACTION_GET.value == action:
        return handle_code_review_get(payload)

    if Action.ACTION_RUN.value == action:
        return handle_code_review_run(payload)

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
