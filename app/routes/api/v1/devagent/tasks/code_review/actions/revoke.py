import fastapi
import pydantic
import celery.result  # type: ignore

from app.devagent.worker import devagent_worker
from app.routes.api.v1.devagent.tasks.validation import validate_query_params


class QueryParams(pydantic.BaseModel):
    task_id: str


class Response(pydantic.BaseModel):
    pass


@validate_query_params(QueryParams)
def action_revoke(query_params: QueryParams) -> Response:
    try:
        parent_task: celery.result.AsyncResult = devagent_worker.AsyncResult(
            query_params.task_id
        )
        if not parent_task.ready():
            parent_task.revoke(terminate=True)
            return Response()

        wrapup_task: celery.result.AsyncResult = devagent_worker.AsyncResult(
            parent_task.result[0][0]
        )
        if not wrapup_task.ready():
            wrapup_task.revoke(terminate=True)

        review_tasks = parent_task.result[0][1][1]
        for review_task_id in review_tasks:
            review_task: celery.result.AsyncResult = devagent_worker.AsyncResult(
                review_task_id[0][0]
            )
            review_task.revoke(terminate=True)

        return Response()
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[code_review_revoke] Exception {type(e)} occured during handling payload {query_params.task_id}: {str(e)}",
        )
