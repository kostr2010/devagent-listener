import fastapi
import enum
import pydantic
import typing
import celery.result  # type: ignore
import celery.states  # type: ignore

from app.devagent.worker import devagent_worker
from app.devagent.stages.review_patches import ReviewPatchResult
from app.devagent.stages.review_wrapup import ProcessedReview, process_review_result
from app.routes.api.v1.devagent.tasks.validation import validate_query_params


class QueryParams(pydantic.BaseModel):
    payload: str


class TaskStatus(enum.IntEnum):
    TASK_STATUS_SUCCESSFUL = 1  # Task completed successfully
    TASK_STATUS_FAILED = 2  # Task completed abnormally
    TASK_STATUS_REVOKED = 3  # Task was cancelled
    TASK_STATUS_PENDING = 4  # Task execution is pending


class Response(pydantic.BaseModel):
    task_id: str
    task_status: int
    task_result: None | str | ProcessedReview


@validate_query_params(QueryParams)
def action_get(query_params: QueryParams) -> Response:
    try:
        parent_task = devagent_worker.AsyncResult(query_params.payload)
        parent_task_status, parent_task_result = _get_task_status_and_result(
            parent_task
        )

        # failed, revoked or pending init
        if parent_task_status != TaskStatus.TASK_STATUS_SUCCESSFUL:
            return Response(
                task_id=parent_task.id,
                task_status=parent_task_status.value,
                task_result=parent_task_result,
            )

        wrapup_task: celery.result.AsyncResult = devagent_worker.AsyncResult(
            parent_task.result[0][0]
        )
        wrapup_task_status, wrapup_task_result = _get_task_status_and_result(
            wrapup_task
        )

        # failed, revoked or successfull wrapup
        if wrapup_task_status != TaskStatus.TASK_STATUS_PENDING:
            return Response(
                task_id=parent_task.id,
                task_status=wrapup_task_status.value,
                task_result=wrapup_task_result,
            )

        review_tasks = parent_task.result[0][1][1]
        review_results = list[list[ReviewPatchResult]]()
        for review_task_id in review_tasks:
            review_task: celery.result.AsyncResult = devagent_worker.AsyncResult(
                review_task_id[0][0]
            )
            review_task_status, review_task_result = _get_task_status_and_result(
                review_task
            )
            if review_task_status == TaskStatus.TASK_STATUS_SUCCESSFUL:
                review_results.append(
                    [
                        ReviewPatchResult.model_validate(res)
                        for res in review_task_result
                    ]
                )

        return Response(
            task_id=parent_task.id,
            task_status=wrapup_task_status,
            task_result=process_review_result(review_results),
        )
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[code_review_get] Exception {type(e)} occured during handling payload {query_params.payload}: {str(e)}",
        )


###########
# private #
###########


def _get_task_status_and_result(
    task: celery.result.AsyncResult,
) -> tuple[TaskStatus, typing.Any]:
    if not task.ready():
        task_status = TaskStatus.TASK_STATUS_PENDING
        task_result = None
    elif task.state == celery.states.REVOKED:
        task_status = TaskStatus.TASK_STATUS_REVOKED
        task_result = None
    elif task.failed():
        task_status = TaskStatus.TASK_STATUS_FAILED
        task_result = str(task.result)
    elif task.successful():
        task_status = TaskStatus.TASK_STATUS_SUCCESSFUL
        task_result = task.result
    else:
        raise Exception(f"Unhandled state of the task {task.id}")
    return task_status, task_result
