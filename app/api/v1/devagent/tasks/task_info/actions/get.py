import redis.asyncio

from app.utils.validation import validate_result
from app.api.v1.devagent.infrastructure import validate_query_params

QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "task_info_get query params schema",
    "description": "Query params schema of task_info_get API",
    "type": "object",
    "properties": {
        "task_id": {
            "description": "Task id of the review",
            "type": "string",
        },
    },
    "required": ["task_id"],
    "additionalProperties": True,
}

RESPONSE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "task_info_get response shema",
    "description": "Response schema of task_info_get API",
    "type": "object",
    "properties": {
        "successfull": {
            "description": "Whether task info was retrieved successfully",
            "type": "boolean",
        },
        "message": {
            "description": "Message in case of failure",
            "type": "string",
        },
        "rev_arkcompiler_development_rules": {
            "description": "Revision of the arkcompiler_development_rules repository used for review",
            "type": "string",
        },
        "rev_devagent": {
            "description": "Revision of the devagent repository used for review",
            "type": "string",
        },
    },
    "patternProperties": {
        # TODO: fix when new rules are added or patch format changes
        "^.*-patch$": {
            "description": "Patch name mapped to the content",
            "type": "string",
        },
        "^ETS.*$": {
            "description": "Rule name mapped to the patch name",
            "type": "string",
        },
        "^rev_.*$": {
            "description": "Repo name mapped to it's revision",
            "type": "string",
        },
    },
    "required": ["successfull"],
    "additionalProperties": False,
}


@validate_result(RESPONSE_SCHEMA)
@validate_query_params(QUERY_PARAMS_SCHEMA)
async def task_info_get(redis: redis.asyncio.Redis, query_params: dict) -> dict:
    try:
        task_id = query_params["task_id"]

        task_info = await redis.hgetall(task_id)

        if task_info == None or len(task_info.keys()) == 0:
            return {
                "successfull": False,
                "message": f"Task info for task {task_id} expired or never existed",
            }

        task_info.update({"successfull": True})
    except Exception as e:
        return {
            "successfull": False,
            "message": f"[task_info_get] Exception occured during handling of task {query_params['task_id']}: {str(e)}",
        }
    else:
        return task_info
