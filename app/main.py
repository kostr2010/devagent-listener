import fastapi
import sqlalchemy.ext.asyncio
import sqlalchemy.future
import validators
import enum
import contextlib
import multiprocessing
import asyncio
import alembic
import alembic.config

from .database import SQL_SESSION
from .models import Task, TaskKind, TaskStatus
from .devagent import devagent_task_code_review_action_run


async def get_db():
    async with SQL_SESSION() as session:
        yield session
        await session.commit()


async def run_migrations():
    cfg = alembic.config.Config("alembic.ini")
    await asyncio.to_thread(alembic.command.upgrade, cfg, "head")


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    print("Initializing listener pool")
    app.state.listener_pool = multiprocessing.Pool(16)
    print("Running migrations")
    await run_migrations()
    yield
    print("Closing listener pool")
    app.state.listener_pool.close()
    app.state.listener_pool.join()


listener = fastapi.FastAPI(debug=True, lifespan=lifespan)


class Action(enum.IntEnum):
    ACTION_GET = 0  # get current state of the task
    ACTION_RUN = 1  # restart execution of the task


@listener.get("/api/v1/devagent")
async def devagent_endpoint(
    response: fastapi.Response,
    request: fastapi.Request,
    background_tasks: fastapi.BackgroundTasks,
    # query parameter declaration
    task_kind: int,
    action: int,
    payload: str | None = None,
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(get_db),
):
    # TODO: add secret key validation

    api_v1_devagent_validate_task_kind(task_kind)
    api_v1_devagent_validate_action(action)

    return await api_v1_devagent_process_task(
        response=response,
        request=request,
        background_tasks=background_tasks,
        task_kind=task_kind,
        action=action,
        payload=payload,
        db=db,
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

    if not payload.isdigit():
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid task id passed in payload parameter: payload={payload}",
        )


async def api_v1_devagent_task_code_review_action_get(
    payload: str | None,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    api_v1_devagent_task_code_review_action_get_validate_payload(payload)

    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(
            Task.task_kind == TaskKind.TASK_KIND_CODE_REVIEW.value,
            Task.task_id == int(payload),
        )
    )

    existing_task = existing_task_result.scalars().first()

    if existing_task == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"No task with task_id={payload} found",
        )

    return existing_task


def api_v1_devagent_task_code_review_action_run_validate_payload(
    payload: str | None,
) -> None:
    if payload == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for payload parameter if task_kind={TaskKind.TASK_KIND_CODE_REVIEW.value} and action={Action.ACTION_RUN.value}",
        )

    if not validators.url(payload):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Invalid url passed in payload: payload={payload}",
        )

    if not ("gitcode" in payload or "gitee" in payload):
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected gitcode url, got payload={payload}",
        )

    # TODO: add more verification


async def api_v1_devagent_task_code_review_action_run(
    background_tasks: fastapi.BackgroundTasks,
    payload: str | None,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    api_v1_devagent_task_code_review_action_run_validate_payload(payload)

    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(
            Task.task_kind == TaskKind.TASK_KIND_CODE_REVIEW.value,
            Task.task_payload == payload,
            Task.task_status == TaskStatus.TASK_STATUS_IN_PROGRESS.value,
        )
    )

    existing_task = existing_task_result.scalars().first()
    if existing_task != None:
        return existing_task

    new_task = Task(
        task_payload=payload,
        task_kind=TaskKind.TASK_KIND_CODE_REVIEW.value,
        task_status=TaskStatus.TASK_STATUS_IN_PROGRESS.value,
    )

    db.add(new_task)

    await db.commit()
    await db.refresh(new_task)

    background_tasks.add_task(
        devagent_task_code_review_action_run,
        task_id=new_task.task_id,
        url=payload,
        db=db,
    )

    return new_task


async def api_v1_devagent_task_code_review(
    request: fastapi.Request,
    background_tasks: fastapi.BackgroundTasks,
    action: int,
    payload: str | None,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    if action == Action.ACTION_GET.value:
        return await api_v1_devagent_task_code_review_action_get(payload=payload, db=db)
    elif action == Action.ACTION_RUN.value:
        return await api_v1_devagent_task_code_review_action_run(
            background_tasks=background_tasks,
            payload=payload,
            db=db,
        )
    else:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Unhandled case in handler of task_kind={TaskKind.TASK_KIND_CODE_REVIEW.value}: action={action}",
        )


async def api_v1_devagent_process_task(
    response: fastapi.Response,
    request: fastapi.Request,
    background_tasks: fastapi.BackgroundTasks,
    task_kind: int,
    action: int,
    payload: str | None,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    if task_kind == TaskKind.TASK_KIND_CODE_REVIEW.value:
        return await api_v1_devagent_task_code_review(
            request=request,
            background_tasks=background_tasks,
            action=action,
            payload=payload,
            db=db,
        )
    else:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Unhandled task_kind={task_kind}",
        )
