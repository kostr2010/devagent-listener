import redis.asyncio
import fastapi
import pydantic
import typing

from app.config import CONFIG
from app.routes.api.v1.devagent.tasks.validation import validate_query_params

from app.redis.models import (
    TASK_INFO_SCHEMA,
    task_info_is_valid_key,
)


# To support other params in query_params
QUERY_PARAMS_SCHEMA = TASK_INFO_SCHEMA.copy()
QUERY_PARAMS_SCHEMA["additionalProperties"] = True


class Response(pydantic.BaseModel):
    pass


@validate_query_params(QUERY_PARAMS_SCHEMA)
async def action_set(
    redis: redis.asyncio.Redis, query_params: dict[str, typing.Any]
) -> Response:
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
