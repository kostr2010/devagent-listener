import redis.asyncio

from app.config import CONFIG
from app.api.v1.devagent.infrastructure import validate_query_params, validate_response

QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "task_info_set query params shema",
    "description": "Query params schema of task_info_set API",
    "type": "object",
    "properties": {
        "task_id": {
            "description": "Task id of the review",
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
    },
    "required": ["task_id", "rev_arkcompiler_development_rules", "rev_devagent"],
    "additionalProperties": True,
}

RESPONSE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "task_info_set response shema",
    "description": "Response schema of task_info_set API",
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
    },
    "required": ["successfull"],
    "additionalProperties": False,
}


@validate_query_params(QUERY_PARAMS_SCHEMA)
@validate_response(RESPONSE_SCHEMA)
async def task_info_set(
    redis: redis.asyncio.Redis, query_params: dict[str, object]
) -> dict[str, object]:
    try:
        task_id = query_params["task_id"]
        rev_arkcompiler_development_rules = query_params[
            "rev_arkcompiler_development_rules"
        ]
        rev_devagent = query_params["rev_devagent"]

        mapping = {
            "rev_arkcompiler_development_rules": rev_arkcompiler_development_rules,
            "rev_devagent": rev_devagent,
        }

        for k, v in query_params.items():
            # TODO: fix when new rules are added or patch format changes
            if k.startswith("ETS") or k.endswith("-patch"):
                mapping.update({k: v})

        vals_written = await redis.hsetex(
            name=task_id, mapping=mapping, ex=CONFIG.EXPIRY_TASK_INFO
        )
        assert vals_written == 1
    except Exception as e:
        return {
            "successfull": False,
            "message": f"[task_info_set] Exception occured during handling of task {task_id}: {str(e)}",
        }
    else:
        return {
            "successfull": True,
        }
