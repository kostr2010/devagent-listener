import fastapi
import enum
import pydantic
import typing

from app.devagent.worker import devagent_worker
from app.devagent.stages.review_wrapup import ProcessedReview
from app.routes.api.v1.devagent.tasks.validation import validate_query_params

QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "code_review_get query params schema",
    "description": "Query params schema of code_review_get API",
    "type": "object",
    "properties": {
        "payload": {
            "description": "Task id of the review",
            "type": "string",
        },
    },
    "required": ["payload"],
    "additionalProperties": True,
}


class TaskStatus(enum.IntEnum):
    TASK_STATUS_SUCCESSFUL = 1  # Task completed successfully
    TASK_STATUS_FAILED = 2  # Task completed abnormally
    TASK_STATUS_PENDING = 4  # Task execution is pending


class Response(pydantic.BaseModel):
    task_id: str
    task_status: int
    task_result: None | str | ProcessedReview


@validate_query_params(QUERY_PARAMS_SCHEMA)
def action_get(
    query_params: dict[str, typing.Any],
) -> Response:
    try:
        payload = query_params["payload"]

        parent_task = devagent_worker.AsyncResult(payload)

        task_status = TaskStatus.TASK_STATUS_PENDING.value
        task_result = None

        # FIXME: for the love of god come up with something better than that
        if parent_task.ready():
            if parent_task.failed():
                task_status = TaskStatus.TASK_STATUS_FAILED.value
                task_result = str(parent_task.result)
            elif parent_task.successful():
                wrapup_task_id = parent_task.result[0][0]
                wrapup_task = devagent_worker.AsyncResult(wrapup_task_id)
                if wrapup_task.ready():
                    if wrapup_task.failed():
                        task_status = TaskStatus.TASK_STATUS_FAILED.value
                        task_result = str(wrapup_task.result)
                    elif wrapup_task.successful():
                        task_status = TaskStatus.TASK_STATUS_SUCCESSFUL.value
                        task_result = wrapup_task.result
                    else:
                        raise Exception("Unhandled wrapup_task state")
            else:
                raise Exception("Unhandled wrapup_task state")
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[code_review_get] Exception {type(e)} occured during handling payload {query_params['payload']}: {str(e)}",
        )
    else:
        return Response(
            task_id=parent_task.id, task_status=task_status, task_result=task_result
        )
