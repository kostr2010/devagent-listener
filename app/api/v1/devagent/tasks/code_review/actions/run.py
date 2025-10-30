import fastapi
import validators
import sqlalchemy.ext.asyncio
import redis.asyncio

from app.devagent.worker import create_devagent_review_workflow


def handle_code_review_run(
    payload: str | None,
):
    _validate_payload(payload)

    urls = _parse_urls(payload)

    task = create_devagent_review_workflow(urls).apply_async()

    print(f"[{task.id}] started task {task.id} for payload {payload}")

    return {"task_id": task.id}


###########
# private #
###########


def _parse_urls(urls: str) -> list:
    return list(filter(lambda s: len(s) > 0, urls.split(";")))


def _validate_payload(
    payload: str | None,
) -> None:
    if payload == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for payload parameter",
        )

    urls = _parse_urls(payload)

    if len(urls) == 0:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty semicolon-separated list of urls for payload",
        )

    for url in urls:
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

    # TODO: add more verification
