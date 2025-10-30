import fastapi
import enum

from app.devagent.worker import devagent_worker


class TaskStatus(enum.IntEnum):
    TASK_STATUS_IN_PROGRESS = 0  # Task is in progress
    TASK_STATUS_DONE = 1  # Task completed successfully
    TASK_STATUS_ERROR = 2  # Task completed abnormally
    TASK_STATUS_ABORTED = 3  # Task execution was aborted
    TASK_STATUS_PENDING = 4  # Task execution is pending


def handle_code_review_get(
    payload: str | None,
):
    _validate_payload(payload)

    task = devagent_worker.AsyncResult(payload)

    if "SUCCESS" == task.state:
        return {
            "task_id": task.id,
            "status": TaskStatus.TASK_STATUS_DONE.value,
            "task_result": task.result,
        }

    if "FAILURE" == task.state:
        return {
            "task_id": task.id,
            "task_status": TaskStatus.TASK_STATUS_ERROR.value,
            "task_result": task.result,
        }

    if "PENDING" == task.state:
        return {
            "task_id": task.id,
            "status": TaskStatus.TASK_STATUS_PENDING.value,
            "task_result": None,
        }

    if "STARTED" == task.state:
        return {
            "task_id": task.id,
            "task_status": TaskStatus.TASK_STATUS_IN_PROGRESS.value,
            "task_result": None,
        }

    raise fastapi.HTTPException(
        status_code=500,
        detail=f"Unexpected task state: payload={payload}, task.state={task.state}",
    )


###########
# private #
###########


def _validate_payload(
    payload: str | None,
) -> None:
    if payload == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for payload",
        )
