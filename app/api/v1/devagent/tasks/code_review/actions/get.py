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
    TASK_STATUS_DONE = 1  # Task completed successfully
    TASK_STATUS_ERROR = 2  # Task completed abnormally
    TASK_STATUS_PENDING = 4  # Task execution is pending


@validate_result(RESPONSE_SCHEMA)
@validate_query_params(QUERY_PARAMS_SCHEMA)
def code_review_get(
    query_params: dict,
):
    # try:
    payload = query_params["payload"]

    task = devagent_worker.AsyncResult(payload)

    task_status = 1
    task_result = ""
    # try:
    task_result = task.get()
    # except Exception as e:
    #     task_result = "hui"
    # try:
    #     task_status = TaskStatus.TASK_STATUS_DONE.value
    #     # FIXME: come up with something better than that
    # except Exception as e:
    #     task_status = TaskStatus.TASK_STATUS_ERROR.value
    #     task_result = str(e)
    # except Exception as e:
    #     return {
    #         "successfull": False,
    #         "message": f"[code_review_get] Exception occured during handling payload {query_params['payload']}: {str(e)}",
    #     }
    # else:
    print(f"redult {task.build_graph(intermediate=True)}")
    return {
        "successfull": True,
        "task_id": task.id,
        "task_status": task_status,
        "task_result": task_result,
    }
