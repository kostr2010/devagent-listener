import fastapi
import validators
import pydantic

from app.devagent.worker import review_init
from app.routes.api.v1.devagent.tasks.validation import validate_query_params


class QueryParams(pydantic.BaseModel):
    payload: str


class Response(pydantic.BaseModel):
    task_id: str


@validate_query_params(QueryParams)
def action_run(query_params: QueryParams) -> Response:
    try:
        urls = _parse_urls(query_params.payload)
        _validate_url_list(urls)
        task = review_init.s(urls).apply_async()
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


def _validate_url_list(urls: list[str]) -> None:
    if len(urls) == 0:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty semicolon-separated list of urls for payload",
        )

    for url in urls:
        _validate_url(url)


def _validate_url(url: str) -> None:
    if not validators.url(url):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid url passed in payload: url={url}",
        )

    if (not "gitcode" in url) or (not "pull" in url):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected gitee / gitcode pull request url, got url={url}",
        )
