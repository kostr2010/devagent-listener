import fastapi
import validators

from app.devagent.worker import create_devagent_review_workflow
from app.utils.validation import validate_result
from app.api.v1.devagent.infrastructure import validate_query_params


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

RESPONSE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "code_review_run response shema",
    "description": "Response schema of code_review_run API",
    "type": "object",
    "properties": {
        "task_id": {
            "description": "Id of the newly started task for this review",
            "type": "boolean",
        },
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


@validate_result(RESPONSE_SCHEMA)
@validate_query_params(QUERY_PARAMS_SCHEMA)
def code_review_run(
    query_params: dict,
) -> dict:
    try:
        payload = query_params["payload"]

        urls = _parse_urls(payload)

        _validate_url_list(urls)

        task = create_devagent_review_workflow(urls).apply_async()

        print(f"started task {task.id} for payload {payload}")
    except Exception as e:
        return {
            "successfull": False,
            "message": f"[code_review_run] Exception occured during handling payload {payload}: {str(e)}",
        }
    else:
        return {"successfull": True, "task_id": task.id}


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

    if not ("gitcode" in url or "gitee" in url) or not "pull" in url:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected gitee / gitcode pull request url, got url={url}",
        )
