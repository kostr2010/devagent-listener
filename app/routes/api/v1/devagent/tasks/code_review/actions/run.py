import fastapi
import pydantic
import asyncio

from app.redis.async_redis import AsyncRedis
from app.db.async_db import AsyncDBSession
from app.diff.provider import DiffProvider
from app.devagent.worker import review_init
from app.routes.api.v1.devagent.tasks.validation import validate_query_params


class QueryParams(pydantic.BaseModel):
    payload: str


class Response(pydantic.BaseModel):
    task_id: str


@validate_query_params(QueryParams)
async def action_run(
    db: AsyncDBSession,
    redis: AsyncRedis,
    diff_provider: DiffProvider,
    query_params: QueryParams,
) -> Response:
    try:
        urls = _parse_urls(query_params.payload)
        diffs = await asyncio.gather(
            *[asyncio.to_thread(diff_provider.get_diff, url) for url in urls]
        )
        task = review_init.s(
            [diff.model_dump() for diff in diffs],
            db.config().model_dump(),
            redis.config().model_dump(),
        ).apply_async()
        print(f"started task {task.id} for payload {query_params.payload}")
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[code_review_run] Exception {type(e)} occured during handling payload {query_params.payload}: {str(e)}",
        )
    else:
        return Response(task_id=task.id)


###########
# private #
###########


def _parse_urls(urls: str) -> list[str]:
    return list(filter(lambda s: len(s) > 0, urls.split(";")))
