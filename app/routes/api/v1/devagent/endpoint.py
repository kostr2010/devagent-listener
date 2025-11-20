import fastapi
import enum
import redis.asyncio

from app.db.async_db import AsyncSession

from app.routes.api.v1.devagent.tasks.code_review.code_review import (
    code_review,
    Response as CodeReviewResponse,
)
from app.routes.api.v1.devagent.tasks.user_feedback.user_feedback import (
    user_feedback,
    Response as UserFeedbackResponse,
)
from app.routes.api.v1.devagent.tasks.task_info.task_info import (
    task_info,
    Response as TaskInfoResponse,
)
from app.routes.api.v1.devagent.tasks.dataset.dataset import (
    dataset,
    Response as DatasetResponse,
)


class TaskKind(enum.IntEnum):
    TASK_KIND_CODE_REVIEW = 0  # Code review
    TASK_KIND_USER_FEEDBACK = 1  # Feedback for the rules
    TASK_KIND_TASK_INFO = 2  # Misc info about the task
    TASK_KIND_DATASET = 3  # Collect db info into dataset


Response = (
    CodeReviewResponse | UserFeedbackResponse | TaskInfoResponse | DatasetResponse
)


async def endpoint_api_v1_devagent(
    response: fastapi.Response,
    request: fastapi.Request,
    db: AsyncSession,
    redis: redis.asyncio.Redis,
    task_kind: int,
    action: int,
) -> Response:
    _validate_task_kind(task_kind)

    query_params = dict(request.query_params)

    if TaskKind.TASK_KIND_CODE_REVIEW.value == task_kind:
        return code_review(action=action, query_params=query_params)

    if TaskKind.TASK_KIND_USER_FEEDBACK.value == task_kind:
        return await user_feedback(
            db=db,
            redis=redis,
            action=action,
            query_params=query_params,
        )

    if TaskKind.TASK_KIND_TASK_INFO.value == task_kind:
        return await task_info(redis=redis, action=action, query_params=query_params)

    if TaskKind.TASK_KIND_DATASET.value == task_kind:
        return await dataset(db=db, action=action, query_params=query_params)

    raise fastapi.HTTPException(
        status_code=500,
        detail=f"[api_v1_devagent_endpoint] Unhandled task_kind={task_kind}",
    )


###########
# private #
###########


def _validate_task_kind(task_kind: int | None) -> None:
    if task_kind not in [e.value for e in TaskKind]:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid task_kind value: task_kind={task_kind}",
        )
