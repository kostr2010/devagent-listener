import fastapi
import pydantic

from app.db.async_db import AsyncSession
from app.routes.api.v1.devagent.tasks.validation import validate_query_params


class QueryParams(pydantic.BaseModel):
    feedback_id: int


class Response(pydantic.BaseModel):
    id: int
    rev_arkcompiler_development_rules: str
    rev_devagent: str
    project: str
    rev_project: str
    patch: str
    rule: str
    file: str
    line: int
    feedback: int


@validate_query_params(QueryParams)
async def action_get(db: AsyncSession, query_params: QueryParams) -> Response:
    try:
        print(query_params.model_dump())
        user_feedback = await db.get_user_feebdack(query_params.feedback_id)

        if user_feedback == None:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"[user_feedback_get] No user feedback found in the db with id {query_params.feedback_id}",
            )
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[user_feedback_get] Exception {type(e)} occured during handling of review {query_params.feedback_id}: {str(e)}",
        )
    else:
        return Response(
            id=user_feedback.id,
            rev_arkcompiler_development_rules=user_feedback.rev_arkcompiler_development_rules,
            rev_devagent=user_feedback.rev_devagent,
            project=user_feedback.project,
            rev_project=user_feedback.rev_project,
            patch=user_feedback.patch,
            rule=user_feedback.rule,
            file=user_feedback.file,
            line=user_feedback.line,
            feedback=user_feedback.feedback,
        )
