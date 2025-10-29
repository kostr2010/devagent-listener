import fastapi
import enum
import sqlalchemy.ext.asyncio
import redis.asyncio


from .tasks.code_review.code_review import handle_code_review
from .tasks.user_feedback.user_feedback import handle_user_feedback


class TaskKind(enum.IntEnum):
    TASK_KIND_CODE_REVIEW = 0  # Code review
    TASK_KIND_USER_FEEDBACK = 1  # Feedback for the rules


async def api_v1_devagent_endpoint(
    response: fastapi.Response,
    request: fastapi.Request,
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    task_kind: int,
    action: int,
    payload: str | None,
) -> dict:
    _validate_task_kind(task_kind)

    if task_kind == TaskKind.TASK_KIND_CODE_REVIEW.value:
        return handle_code_review(
            postgres=postgres,
            redis=redis,
            action=action,
            payload=payload,
        )

    if task_kind == TaskKind.TASK_KIND_USER_FEEDBACK.value:
        return await handle_user_feedback(
            action=action,
            payload=payload,
        )

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
