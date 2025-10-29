import fastapi
import celery.exceptions
import enum

from app.devagent.worker import devagent_worker
from app.utils.validation import validate_result
from app.api.v1.devagent.infrastructure import validate_query_params

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

RESPONSE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "code_review_get response shema",
    "description": "Response schema of code_review_get API",
    "type": "object",
    "properties": {
        "task_id": {
            "description": "Id of the requested task",
            "type": "string",
        },
        "task_status": {
            "description": "Status of the task",
            "type": "number",
        },
        "task_result": {
            "description": "Result of the task",
            "oneOf": [
                {"type": "null"},
                {"type": "string"},
                {
                    "type": "object",
                    "properties": {
                        "errors": {
                            "type": "object",
                            "patternProperties": {
                                "^.*$": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "patch": {"type": "string"},
                                            "rule": {"type": "string"},
                                        },
                                        "required": ["message", "patch", "rule"],
                                        "additionalProperties": False,
                                    },
                                },
                            },
                            "additionalProperties": False,
                        },
                        "results": {
                            "type": "object",
                            "patternProperties": {
                                "^.*$": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "file": {"type": "string"},
                                            "line": {"type": "number"},
                                            "rule": {"type": "string"},
                                            "severity": {"type": "string"},
                                            "message": {"type": "string"},
                                            "code_snippet": {"type": "string"},
                                        },
                                        "required": [
                                            "file",
                                            "line",
                                            "rule",
                                            "message",
                                        ],
                                        # FIXME: remove after devagent fixes it's schema
                                        "additionalProperties": True,
                                    },
                                },
                            },
                            "additionalProperties": False,
                        },
                    },
                    "required": ["errors", "results"],
                    "additionalProperties": False,
                },
            ],
        },
    },
    "required": ["task_id", "task_status", "task_result"],
    "additionalProperties": False,
}


class TaskStatus(enum.IntEnum):
    TASK_STATUS_SUCCESSFUL = 1  # Task completed successfully
    TASK_STATUS_FAILED = 2  # Task completed abnormally
    TASK_STATUS_PENDING = 4  # Task execution is pending


@validate_result(RESPONSE_SCHEMA)
@validate_query_params(QUERY_PARAMS_SCHEMA)
def code_review_get(
    query_params: dict,
):
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
            detail=f"[code_review_get] Exception occured during handling payload {query_params['payload']}: {str(e)}",
        )
    else:
        return {
            "task_id": parent_task.id,
            "task_status": task_status,
            "task_result": task_result,
        }
