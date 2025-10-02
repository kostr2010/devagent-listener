import fastapi
import sqlalchemy.ext.asyncio
import sqlalchemy.future
import validators

from .database import SQL_ENGINE, SQL_SESSION
from .models import SQL_BASE, Task, TaskKind, TaskStatus
from .schemas import StartReviewResponse


async def get_db():
    async with SQL_SESSION() as session:
        yield session
        await session.commit()


listener = fastapi.FastAPI(debug=True)


@listener.get("/hi")
async def hi():
    return {"message": "hi"}


@listener.get("/api/v1/start_review", response_model=StartReviewResponse)
async def start_review(
    response: fastapi.Response,
    request: fastapi.Request,
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(get_db),
):
    URL = request.query_params.get("url")

    if not URL:
        raise fastapi.HTTPException(
            status_code=400, detail=f"Expected url parameter, got url={URL}"
        )

    if not validators.url(URL):
        raise fastapi.HTTPException(
            status_code=400, detail=f"Invalid url passed: url={URL}"
        )

    if not "gitcode" in URL:
        raise fastapi.HTTPException(
            status_code=400, detail=f"Expected gitcode url, got url={URL}"
        )

    # TODO: add secret key validation

    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(
            Task.task_kind == TaskKind.TASK_KIND_CODE_REVIEW,
            Task.task_status == TaskStatus.TASK_STATUS_IN_PROGRESS,
            Task.payload == URL,
        )
    )
    existing_task = existing_task_result.scalars().first()
    if existing_task is not None:
        print(f"Task for url {URL} is already in progress (id={existing_task.task_id})")
        return {"task_id": f"{existing_task.task_id}"}

    new_task = Task(
        payload=URL,
        task_kind=TaskKind.TASK_KIND_CODE_REVIEW,
        task_status=TaskStatus.TASK_STATUS_IN_PROGRESS,
    )
    db.add(new_task)

    await db.commit()
    await db.refresh(new_task)

    print(f"Created new task for url {URL} (id={new_task.task_id})")

    return {"task_id": f"{new_task.task_id}"}


@listener.get("/api/v1/check_task/{task_id}")
async def check_review(
    task_id: int,
    response: fastapi.Response,
    request: fastapi.Request,
    db: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(get_db),
):
    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(Task.task_id == task_id)
    )

    existing_task = existing_task_result.scalars().first()

    if existing_task is None:
        raise fastapi.HTTPException(status_code=404, detail="Task not found")

    return existing_task
