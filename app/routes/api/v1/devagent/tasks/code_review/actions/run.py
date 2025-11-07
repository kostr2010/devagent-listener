import fastapi
import validators
import pydantic
import typing

from app.devagent.worker import launch_review
from app.routes.api.v1.devagent.tasks.validation import validate_query_params


QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "code_review_run query params schema",
    "description": "Query params schema of code_review_run API",
    "type": "object",
    "properties": {
        "payload": {
            "description": "Semicolon-separated list of urls for review",
            "type": "string",
        },
    },
    "required": ["payload"],
    "additionalProperties": True,
}


class Response(pydantic.BaseModel):
    task_id: str


@validate_query_params(QUERY_PARAMS_SCHEMA)
def action_run(
    query_params: dict[str, typing.Any],
) -> Response:
    try:
        payload = query_params["payload"]

        urls = _parse_urls(payload)

        _validate_url_list(urls)

        task = launch_review.s(urls).apply_async()

        print(f"started task {task.id} for payload {payload}")
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[code_review_run] Exception {type(e)} occured during handling payload {query_params['payload']}: {str(e)}",
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
