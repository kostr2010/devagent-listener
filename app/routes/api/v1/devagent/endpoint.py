import fastapi
import enum

from app.redis.async_redis import AsyncRedis
from app.db.async_db import AsyncDBSession
from app.diff.provider import DiffProvider
from app.nexus.repo import NexusRepo

from app.routes.api.v1.devagent.tasks.code_review.code_review import (
    code_review,
    Response as CodeReviewResponse,
)
from app.routes.api.v1.devagent.tasks.user_feedback.user_feedback import (
    user_feedback,
    Response as UserFeedbackResponse,
)
from app.routes.api.v1.devagent.tasks.dataset.dataset import (
    dataset,
    Response as DatasetResponse,
)


class TaskKind(enum.IntEnum):
    TASK_KIND_CODE_REVIEW = 0  # Code review
    TASK_KIND_USER_FEEDBACK = 1  # Feedback for the rules
    TASK_KIND_DATASET = 3  # Collect db info into dataset


Response = CodeReviewResponse | UserFeedbackResponse | DatasetResponse


async def endpoint_api_v1_devagent(
    request: fastapi.Request,
    db: AsyncDBSession,
    redis: AsyncRedis,
    nexus: NexusRepo,
    diff_provider: DiffProvider,
    task_kind: int,
    action: int,
) -> Response:
    _validate_task_kind(task_kind)

    query_params = dict(request.query_params)

    if TaskKind.TASK_KIND_CODE_REVIEW.value == task_kind:
        return await code_review(
            db=db,
            redis=redis,
            action=action,
            diff_provider=diff_provider,
            query_params=query_params,
        )

    if TaskKind.TASK_KIND_USER_FEEDBACK.value == task_kind:
        return await user_feedback(
            db=db,
            redis=redis,
            action=action,
            query_params=query_params,
        )

    if TaskKind.TASK_KIND_DATASET.value == task_kind:
        return await dataset(db=db, nexus=nexus, action=action)

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
