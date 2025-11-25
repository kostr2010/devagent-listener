import fastapi
import pydantic

from app.db.async_db import AsyncSession
from app.routes.api.v1.devagent.tasks.validation import validate_query_params


class QueryParams(pydantic.BaseModel):
    feedback_id: int
    feedback: int


class Response(pydantic.BaseModel):
    pass


@validate_query_params(QueryParams)
async def action_update(db: AsyncSession, query_params: QueryParams) -> Response:
    try:
        print(query_params.model_dump())
        user_feedback = await db.get_user_feebdack(query_params.feedback_id)

        if user_feedback == None:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"[user_feedback_update] No user feedback found in the db with id {query_params.feedback_id}",
            )

        await db.update_user_feebdack(int(user_feedback.id), query_params.feedback)
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[user_feedback_update] Exception {type(e)} occured during handling of review {query_params.feedback_id}: {str(e)}",
        )
    else:
        return Response()
