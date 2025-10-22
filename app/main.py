import fastapi
import validators
import enum
import contextlib
import logging
import redis.asyncio

from .redis import init_async_redis_conn
from .devagent.worker import devagent_review_workflow, devagent_worker
from .config import CONFIG

LISTENER_LOG = logging.getLogger(__name__)
LISTENER_LOG.setLevel(logging.INFO)


class TaskKind(enum.IntEnum):
    TASK_KIND_CODE_REVIEW = 0  # Code review


class TaskStatus(enum.IntEnum):
    TASK_STATUS_IN_PROGRESS = 0  # Task is in progress
    TASK_STATUS_DONE = 1  # Task completed successfully
    TASK_STATUS_ERROR = 2  # Task completed abnormally
    TASK_STATUS_ABORTED = 3  # Task execution was aborted
    TASK_STATUS_PENDING = 4  # Task execution is pending


class Action(enum.IntEnum):
    ACTION_GET = 0  # get current state of the task
    ACTION_RUN = 1  # restart execution of the task


def encode_devagent_review_payload(payload: str) -> str:
    return f"{TaskKind.TASK_KIND_CODE_REVIEW.value}:{payload}"


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    print("Initializing redis connection")
    app.state.async_redis_conn = init_async_redis_conn(CONFIG.LISTENER_REDIS_DB)
    yield
    print("Closing redis connection")
    await app.state.async_redis_conn.close()


def get_redis(request: fastapi.Request):
    return request.app.state.async_redis_conn


listener = fastapi.FastAPI(debug=True, lifespan=lifespan)


@listener.get("/health")
def health_endpoint():
    return {"status": "healthy"}


@listener.get("/api/v1/devagent")
async def devagent_endpoint(
    response: fastapi.Response,
    request: fastapi.Request,
    # query parameter declaration
    task_kind: int,
    action: int,
    payload: str | None = None,
    redis: redis.asyncio.Redis = fastapi.Depends(get_redis),
):
    # TODO: add secret key validation

    print(
        f"Received request /api/v1/devagent?task_kind={task_kind}&action={action}&payload={payload}"
    )

    api_v1_devagent_validate_task_kind(task_kind)
    api_v1_devagent_validate_action(action)

    return await api_v1_devagent_process_task(
        response=response,
        request=request,
        task_kind=task_kind,
        action=action,
        payload=payload,
        redis=redis,
    )


def api_v1_devagent_validate_task_kind(task_kind: int | None) -> None:
    if task_kind == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for task_kind parameter",
        )

    if task_kind not in [e.value for e in TaskKind]:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid task_kind value: task_kind={task_kind}",
        )


def api_v1_devagent_validate_action(action: int | None) -> None:
    if action == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for action parameter",
        )

    if action not in [e.value for e in Action]:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid action value: action={action}",
        )


def api_v1_devagent_task_code_review_action_get_validate_payload(
    payload: str | None,
) -> None:
    if payload == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for payload parameter if task_kind={TaskKind.TASK_KIND_CODE_REVIEW.value} and action={Action.ACTION_GET.value}",
        )


async def api_v1_devagent_task_code_review_action_get(
    payload: str | None,
):
    api_v1_devagent_task_code_review_action_get_validate_payload(payload)

    task = devagent_worker.AsyncResult(payload)

    if "SUCCESS" == task.state:
        return {
            "task_id": task.id,
            "status": TaskStatus.TASK_STATUS_DONE.value,
            "task_result": task.result,
        }
    elif "FAILURE" == task.state:
        return {
            "task_id": task.id,
            "task_status": TaskStatus.TASK_STATUS_ERROR.value,
            "task_result": str(task.result),
        }
    if "PENDING" == task.state:
        return {
            "task_id": task.id,
            "status": TaskStatus.TASK_STATUS_PENDING.value,
            "task_result": None,
        }
    elif "STARTED" == task.state:
        return {
            "task_id": task.id,
            "task_status": TaskStatus.TASK_STATUS_IN_PROGRESS.value,
            "task_result": None,
        }
    else:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Unexpected task state: payload={payload}, task.state={task.state}",
        )


def api_v1_devagent_task_code_review_action_run_validate_payload(
    payload: str | None,
) -> None:
    if payload == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for payload parameter if task_kind={TaskKind.TASK_KIND_CODE_REVIEW.value} and action={Action.ACTION_RUN.value}",
        )

    urls = list(filter(lambda s: len(s) > 0, payload.split(";")))

    if len(urls) == 0:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty semicolon-separated list of urls for payload parameter if task_kind={TaskKind.TASK_KIND_CODE_REVIEW.value} and action={Action.ACTION_RUN.value}",
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
                detail=f"Expected gitee/ gitcode pull request url, got url={url}",
            )

    # TODO: add more verification


async def api_v1_devagent_task_code_review_action_run(
    payload: str | None,
    redis: redis.asyncio.Redis,
):
    api_v1_devagent_task_code_review_action_run_validate_payload(payload)

    urls = list(filter(lambda s: len(s) > 0, payload.split(";")))

    print(f"devagent_review parsed urls: {urls}")

    task = devagent_review_workflow(urls).apply_async()

    print(f"started task {task.id}")

    encoded_payload = encode_devagent_review_payload(payload)

    # get running task for the same payload
    existing_task = await redis.get(encoded_payload)

    print(f"existing task {existing_task}")

    # immediately override with new task
    await redis.set(encoded_payload, task.id, ex=3600)

    print(f"new task {await redis.get(encoded_payload)}")

    # terminate running task if it was
    if existing_task:
        devagent_worker.control.revoke(existing_task, terminate=True)

    # return new task
    return {"task_id": task.id}


async def api_v1_devagent_task_code_review(
    action: int,
    payload: str | None,
    redis: redis.asyncio.Redis,
):
    if action == Action.ACTION_GET.value:
        return await api_v1_devagent_task_code_review_action_get(payload=payload)
    elif action == Action.ACTION_RUN.value:
        return await api_v1_devagent_task_code_review_action_run(
            payload=payload,
            redis=redis,
        )
    else:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Unhandled case in handler of task_kind={TaskKind.TASK_KIND_CODE_REVIEW.value}: action={action}",
        )


async def api_v1_devagent_process_task(
    response: fastapi.Response,
    request: fastapi.Request,
    task_kind: int,
    action: int,
    payload: str | None,
    redis: redis.asyncio.Redis,
):
    request  # maybe used
    response  # maybe used

    if task_kind == TaskKind.TASK_KIND_CODE_REVIEW.value:
        return await api_v1_devagent_task_code_review(
            action=action,
            payload=payload,
            redis=redis,
        )
    else:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Unhandled task_kind={task_kind}",
        )
