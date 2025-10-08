import asyncio
import sqlalchemy.ext.asyncio
import sqlalchemy.future
import fastapi

from .models import Task, TaskKind, TaskStatus


async def devagent_task_code_review_action_run(
    task_id: int, url: str, db: sqlalchemy.ext.asyncio.AsyncSession
):
    # process url, execute LLM request
    await asyncio.sleep(30)
    devagent_status = TaskStatus.TASK_STATUS_DONE
    devagent_result = "sample result"

    # update task after LLM finished work
    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(Task.task_id == task_id)
    )

    db_item = existing_task_result.scalars().first()

    if db_item == None:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"No task {task_id} found in the db after code_review for {url} has finished",
        )

    db_item.task_status = devagent_status.value
    db_item.task_result = devagent_result
    db_item.updated_at = sqlalchemy.text("now()")

    await db.commit()
    await db.refresh(db_item)
