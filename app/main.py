import fastapi
import sqlalchemy.ext.asyncio
import sqlalchemy.future
import validators
import enum

from .database import SQL_SESSION
from .models import Task, TaskKind, TaskStatus
from .request_param import RequestParam, validate_request_params, register_request_param


async def get_db():
    async with SQL_SESSION() as session:
        yield session
        await session.commit()


listener = fastapi.FastAPI(debug=True)


class Action(enum.IntEnum):
    ACTION_GET = 0  # get current state of the task
    ACTION_RUN = 1  # restart execution of the task


API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND = "task_kind"
API_V1_DEVAGENT_REQUEST_PARAM_ACTION = "action"
API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD = "payload"


@listener.get("/api/v1/devagent")
async def start_review(
    response: fastapi.Response,
    request: fastapi.Request,
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(get_db),
):
    # TODO: add secret key validation

    params: list[RequestParam] = []
    register_request_param(
        name=API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND,
        default_value=None,
        validator=api_v1_devagent_validate_task_kind,
        param_list=params,
    )
    register_request_param(
        name=API_V1_DEVAGENT_REQUEST_PARAM_ACTION,
        default_value=str(Action.ACTION_GET.value),
        validator=api_v1_devagent_validate_action,
        param_list=params,
    )
    register_request_param(
        name=API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD,
        default_value=None,
        validator=None,
        param_list=params,
    )
    validate_request_params(params=params, request=request)

    return await api_v1_devagent_process_task(response=response, request=request, db=db)


def api_v1_devagent_validate_task_kind(kind: str | None) -> None:
    if kind == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for {API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND} parameter",
        )

    if kind not in [str(e.value) for e in TaskKind]:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid {API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND} value: {API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND}={kind}",
        )


def api_v1_devagent_validate_action(kind: str | None) -> None:
    if kind == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for {API_V1_DEVAGENT_REQUEST_PARAM_ACTION} parameter",
        )

    if kind not in [str(e.value) for e in Action]:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid {API_V1_DEVAGENT_REQUEST_PARAM_ACTION} value: {API_V1_DEVAGENT_REQUEST_PARAM_ACTION}={kind}",
        )


def api_v1_devagent_process_task_code_review_validate_payload(
    payload: str | None,
) -> None:
    if payload == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for {API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD} parameter if {API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND}={TaskKind.TASK_KIND_CODE_REVIEW.value}",
        )

    if not validators.url(payload):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid url passed in {API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD}: {API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD}={payload}",
        )

    if not "gitcode" in payload:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected gitcode url, got {API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD}={payload}",
        )

    # TODO: add more verification


async def api_v1_devagent_process_task_code_review_get(
    request: fastapi.Request,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    url = request.query_params.get(API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD)
    api_v1_devagent_process_task_code_review_validate_payload(url)

    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(
            Task.task_kind == TaskKind.TASK_KIND_CODE_REVIEW.value,
            Task.payload == url,
        )
    )

    existing_task = existing_task_result.scalars().first()

    return existing_task


async def api_v1_devagent_process_task_code_review_rerun(
    request: fastapi.Request,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    url = request.query_params.get(API_V1_DEVAGENT_REQUEST_PARAM_PAYLOAD)
    api_v1_devagent_process_task_code_review_validate_payload(url)

    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(
            Task.task_kind == TaskKind.TASK_KIND_CODE_REVIEW.value,
            Task.payload == url,
        )
    )
    db_item = existing_task_result.scalars().first()
    if db_item != None:
        await db.delete(db_item)
        await db.commit()

    new_task = Task(
        payload=url,
        task_kind=TaskKind.TASK_KIND_CODE_REVIEW.value,
        task_status=TaskStatus.TASK_STATUS_IN_PROGRESS.value,
    )
    db.add(new_task)

    await db.commit()
    await db.refresh(new_task)

    return new_task


async def api_v1_devagent_process_task_code_review(
    request: fastapi.Request,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    action = request.query_params.get(API_V1_DEVAGENT_REQUEST_PARAM_ACTION)

    if action == str(Action.ACTION_GET.value):
        return await api_v1_devagent_process_task_code_review_get(
            request=request, db=db
        )
    elif action == str(Action.ACTION_RUN.value):
        return await api_v1_devagent_process_task_code_review_rerun(
            request=request, db=db
        )
    else:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Unhandled case in handler of {API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND}={TaskKind.TASK_KIND_CODE_REVIEW.value}: {API_V1_DEVAGENT_REQUEST_PARAM_ACTION}={action}",
        )


async def api_v1_devagent_process_task(
    response: fastapi.Response,
    request: fastapi.Request,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    task_kind = request.query_params.get(API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND)
    if task_kind == str(TaskKind.TASK_KIND_CODE_REVIEW.value):
        return await api_v1_devagent_process_task_code_review(request=request, db=db)
    else:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Unhandled {API_V1_DEVAGENT_REQUEST_PARAM_TASK_KIND}={task_kind}",
        )
