import jsonschema
import redis.asyncio
import fastapi
import pydantic
import typing

from app.config import CONFIG
from app.redis.models import TASK_INFO_SCHEMA, task_info_is_valid_key


class Response(pydantic.BaseModel):
    pass


async def action_set(
    redis: redis.asyncio.Redis, query_params: dict[str, typing.Any]
) -> Response:
    try:
        # FIXME: make pydantic model for redis TaskInfo and validate using validate_query_params
        schema = TASK_INFO_SCHEMA.copy()
        schema["additionalProperties"] = True
        jsonschema.validate(query_params, schema)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Error while validating action_set's query_params : {str(e)}",
        )

    try:
        task_id = str(query_params["task_id"])
        task_info = dict(
            (k, str(v)) for k, v in query_params.items() if task_info_is_valid_key(k)
        )

        # since async redis is used, it is always Awaitable
        vals_written = await redis.hsetex(
            name=task_id, mapping=task_info, ex=CONFIG.EXPIRY_TASK_INFO
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
