import fastapi
import enum
import sqlalchemy.ext.asyncio
import redis.asyncio


from .tasks.code_review.code_review import handle_code_review
from .tasks.user_feedback.user_feedback import handle_user_feedback
from .tasks.task_info.task_info import handle_task_info


class TaskKind(enum.IntEnum):
    TASK_KIND_CODE_REVIEW = 0  # Code review
    TASK_KIND_USER_FEEDBACK = 1  # Feedback for the rules
    TASK_KIND_TASK_INFO = 2  # Misc info about the task


async def api_v1_devagent_endpoint(
    response: fastapi.Response,
    request: fastapi.Request,
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    task_kind: int,
    action: int,
) -> dict:
    _validate_task_kind(task_kind)

    if TaskKind.TASK_KIND_CODE_REVIEW.value == task_kind:
        return handle_code_review(action=action, query_params=request.query_params)

    if TaskKind.TASK_KIND_USER_FEEDBACK.value == task_kind:
        return await handle_user_feedback(
            postgres=postgres,
            redis=redis,
            action=action,
            query_params=request.query_params,
        )

    if TaskKind.TASK_KIND_TASK_INFO.value == task_kind:
        return await handle_task_info(
            redis=redis, action=action, query_params=request.query_params
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
