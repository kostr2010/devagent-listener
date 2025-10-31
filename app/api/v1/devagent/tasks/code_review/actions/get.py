import fastapi
import enum

from app.devagent.worker import devagent_worker
from app.api.v1.devagent.infrastructure import validate_query_params, validate_response

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
        "successfull": {
            "description": "Whether feedback was stored successfully",
            "type": "boolean",
        },
        "message": {
            "description": "Message in case of failure",
            "type": "string",
        },
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
                                            "message": {
                                                "type": "string",
                                            },
                                            "patch": {
                                                "type": "string",
                                            },
                                            "rule": {
                                                "type": "string",
                                            },
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
                                            "file": {
                                                "type": "string",
                                            },
                                            "line": {
                                                "type": "number",
                                            },
                                            "rule": {
                                                "type": "string",
                                            },
                                            "severity": {
                                                "type": "string",
                                            },
                                            "rule": {
                                                "type": "string",
                                            },
                                            "message": {
                                                "type": "string",
                                            },
                                            "code_snippet": {
                                                "type": "string",
                                            },
                                        },
                                        "required": [
                                            "file",
                                            "line",
                                            "rule",
                                            "severity",
                                            "rule",
                                            "message",
                                            "code_snippet",
                                        ],
                                        "additionalProperties": False,
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
    "required": ["successfull"],
    "additionalProperties": False,
}


class TaskStatus(enum.IntEnum):
    TASK_STATUS_IN_PROGRESS = 0  # Task is in progress
    TASK_STATUS_DONE = 1  # Task completed successfully
    TASK_STATUS_ERROR = 2  # Task completed abnormally
    TASK_STATUS_ABORTED = 3  # Task execution was aborted
    TASK_STATUS_PENDING = 4  # Task execution is pending


@validate_query_params(QUERY_PARAMS_SCHEMA)
@validate_response(RESPONSE_SCHEMA)
def code_review_get(
    query_params: dict,
):
    try:
        payload = query_params["task_id"]

        task = devagent_worker.AsyncResult(payload)

        task_status = None

        if "SUCCESS" == task.state:
            task_status = (TaskStatus.TASK_STATUS_DONE.value,)
        elif "FAILURE" == task.state:
            task_status = TaskStatus.TASK_STATUS_ERROR.value
        elif "PENDING" == task.state:
            task_status = TaskStatus.TASK_STATUS_PENDING.value
        elif "STARTED" == task.state:
            task_status = TaskStatus.TASK_STATUS_IN_PROGRESS.value
        else:
            raise fastapi.HTTPException(
                status_code=500,
                detail=f"Unexpected task state: payload={payload}, task.state={task.state}",
            )
    except Exception as e:
        return {
            "successfull": False,
            "message": f"[code_review_get] Exception occured during handling payload {payload}: {str(e)}",
        }
    else:
        return {
            "successfull": True,
            "task_id": task.id,
            "task_status": task_status,
            "task_result": task.result,
        }
