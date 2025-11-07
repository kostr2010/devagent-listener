import redis.asyncio
import fastapi
import pydantic
import typing

from app.config import CONFIG
from app.routes.api.v1.devagent.tasks.validation import validate_query_params

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
            "description": "Repo name mapped to it's revision",
            "type": "string",
        },
    },
    "required": [
        "task_id",
        "rev_nazarovkonstantin/arkcompiler_development_rules",
        "rev_egavrin/devagent",
    ],
    "additionalProperties": True,
}


class Response(pydantic.BaseModel):
    pass


@validate_query_params(QUERY_PARAMS_SCHEMA)
async def action_set(
    redis: redis.asyncio.Redis, query_params: dict[str, typing.Any]
) -> Response:
    try:
        task_id = str(query_params["task_id"])
        rev_arkcompiler_development_rules = query_params[
            "rev_nazarovkonstantin/arkcompiler_development_rules"
        ]
        rev_devagent = query_params["rev_egavrin/devagent"]

        mapping = {
            "rev_nazarovkonstantin/arkcompiler_development_rules": rev_arkcompiler_development_rules,
            "rev_egavrin/devagent": rev_devagent,
        }

        for k, v in query_params.items():
            # TODO: fix when new rules are added or patch format changes
            if k.startswith("ETS") or k.startswith("patch_") or k.startswith("rev_"):
                mapping.update({k: v})

        # since async redis is used, it is always Awaitable
        vals_written = await redis.hsetex(
            name=task_id, mapping=mapping, ex=CONFIG.EXPIRY_TASK_INFO
        )  # type: ignore
        assert vals_written == 1
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[task_info_set] Exception {type(e)} occured during handling of task {query_params['task_id']}: {str(e)}",
        )
    else:
        return Response()
