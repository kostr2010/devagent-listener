import enum
import fastapi
import typing

from app.db.async_db import AsyncDBSession
from app.nexus.repo import NexusRepo

from app.routes.api.v1.devagent.tasks.dataset.actions.errors import (
    action_errors,
    Response as ErrorsResponse,
)
from app.routes.api.v1.devagent.tasks.dataset.actions.user_feedback import (
    action_user_feedback,
    Response as UserFeedbackResponse,
)


class Action(enum.IntEnum):
    ACTION_ERRORS = 0
    ACTION_USER_FEEDBACK = 1


Response = ErrorsResponse | UserFeedbackResponse


async def dataset(
    db: AsyncDBSession,
    nexus: NexusRepo,
    action: int,
) -> Response:
    """Create dataset from the information stored in db

    Args:
        db (AsyncSession): db connection used to query database
        action (int): Action required by the endpoint. Can be one of the `Action` enum
        query_params (dict[str, typing.Any]): Payload for the endpoint. Interpreted differently depending on the action

    Raises:
        fastapi.HTTPException: in case of internal server errors or invalid user inputs

    Returns:
        Response: answer, depends on the action
    """

    _validate_action(action)

    if Action.ACTION_ERRORS.value == action:
        return await action_errors(db=db, nexus=nexus)

    if Action.ACTION_USER_FEEDBACK.value == action:
        return await action_user_feedback(db=db, nexus=nexus)

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
