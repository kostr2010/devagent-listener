import redis.asyncio
import fastapi
import typing

from app.routes.api.v1.devagent.tasks.validation import (
    validate_query_params,
    validate_result,
)

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


Response = dict[str, str]


# FIXME: remove validation through schema, make it pydantic
@validate_result(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "task_info_get response shema",
        "description": "Response schema of task_info_get API",
        "type": "object",
        "properties": {
            "rev_nazarovkonstantin/arkcompiler_development_rules": {
                "description": "Revision of the arkcompiler_development_rules repository used for review",
                "type": "string",
            },
            "rev_egavrin/devagent": {
                "description": "Revision of the devagent repository used for review",
                "type": "string",
            },
        },
        "patternProperties": {
            # TODO: fix when new rules are added or patch format changes
            "^patch_.*$": {
                "description": "Patch name mapped to the content",
                "type": "string",
            },
            "^ETS.*$": {
                "description": "Rule name mapped to the patch name",
                "type": "string",
            },
            "^rev_.*/.*$": {
                "description": "Project name mapped to it's revision",
                "type": "string",
            },
        },
        "required": [
            "rev_nazarovkonstantin/arkcompiler_development_rules",
            "rev_egavrin/devagent",
        ],
        "additionalProperties": False,
    }
)
@validate_query_params(QUERY_PARAMS_SCHEMA)
async def action_get(
    redis: redis.asyncio.Redis, query_params: dict[str, typing.Any]
) -> Response:
    try:
        task_id = query_params["task_id"]
        # since async redis is used, it is always Awaitable
        task_info = await redis.hgetall(task_id)  # type: ignore

        if len(task_info.keys()) == 0:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Task info for task {task_id} expired or never existed",
            )

        decoded = dict()
        for k, v in task_info.items():
            decoded.update({k.decode("utf-8"): v.decode("utf-8")})
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[task_info_get] Exception {type(e)} occured during handling of task {query_params['task_id']}: {str(e)}",
        )
    else:
        return decoded
