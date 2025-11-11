import sqlalchemy.ext.asyncio
import sqlalchemy.future
import os
import fastapi
import pydantic
import typing
import tempfile
import shutil
import datetime

from app.routes.api.v1.devagent.tasks.validation import validate_query_params
from app.postgres.models import UserFeedback, Patch, Feedback

QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "user_feedback_set query params schema",
    "description": "Query params schema of user_feedback_set API",
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": True,
}


class Response(pydantic.BaseModel):
    archive: str


@validate_query_params(QUERY_PARAMS_SCHEMA)
async def action_user_feedback(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    query_params: dict[str, typing.Any],
) -> Response:
    try:
        wd = tempfile.mkdtemp()

        query_res = await postgres.execute(sqlalchemy.future.select(UserFeedback))
        user_feedback = query_res.scalars().all()

        for feedback in user_feedback:
            feedback_wd = os.path.abspath(
                os.path.join(
                    wd,
                    str(feedback.rule),
                    Feedback(int(feedback.feedback)).name,
                    str(feedback.id),
                )
            )
            os.makedirs(feedback_wd, exist_ok=True)

            env_file = os.path.join(feedback_wd, ".env")
            with open(env_file, "w") as e:
                e.write(f"PROJECT={feedback.project}\n")
                e.write(f"REV_PROJECT={feedback.rev_project}\n")
                e.write(f"REV_DEV_RULES={feedback.rev_devagent}\n")
                e.write(f"REV_DEVAGENT={feedback.rev_arkcompiler_development_rules}\n")
                e.write(f"RULE={feedback.rule}\n")
                e.write(f"FILE={feedback.file}\n")
                e.write(f"LINE={feedback.line}\n")

            r = await postgres.execute(
                sqlalchemy.future.select(Patch).where(Patch.id == feedback.patch)
            )
            patch = r.scalars().first()

            if patch == None:
                raise Exception(f"Could not get patch {feedback.patch} from the db")

            patch_file = os.path.join(feedback_wd, str(feedback.patch))
            with open(patch_file, "w") as p:
                patch_content = str(patch.content)
                p.write(patch_content)

        archive = os.path.join(
            tempfile.mkdtemp(), f"feedback-{datetime.datetime.now().date()}"
        )
        shutil.make_archive(archive, "zip", wd, ".")
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[user_feedback_set] Exception {type(e)} occured during handling of task dataset user_feedback: {str(e)}",
        )
    else:
        return Response(archive=f"{archive}.zip")
