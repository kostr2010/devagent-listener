import redis.asyncio
import fastapi
import typing

from app.routes.api.v1.devagent.tasks.validation import (
    validate_query_params,
    validate_result,
)
from app.redis.models import TASK_INFO_SCHEMA


QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
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


# FIXME: remove result validation through schema, make it pydantic
@validate_result(TASK_INFO_SCHEMA)
@validate_query_params(QUERY_PARAMS_SCHEMA)
async def action_get(
    redis: redis.asyncio.Redis, query_params: dict[str, typing.Any]
) -> Response:
    try:
        task_id = str(query_params["task_id"])
        # since async redis is used, it is always Awaitable
        task_info = await redis.hgetall(task_id)  # type: ignore

        if len(task_info.keys()) == 0:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Task info for task {task_id} expired or never existed",
            )

        decoded = dict(
            (k.decode("utf-8"), v.decode("utf-8")) for k, v in task_info.items()
        )
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[task_info_get] Exception {type(e)} occured during handling of task {query_params['task_id']}: {str(e)}",
        )
    else:
        return decoded
