import os
import fastapi
import pydantic
import tempfile
import shutil
import datetime

from app.db.async_db import AsyncDBSession
from app.db.schemas.user_feedback import Feedback
from app.nexus.repo import NexusRepo


class Response(pydantic.BaseModel):
    archive: str


async def action_user_feedback(db: AsyncDBSession, nexus: NexusRepo) -> Response:
    try:
        wd = tempfile.mkdtemp()

        user_feedback = await db.select_user_feebdack(None)

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

            patch = await db.get_patch(str(feedback.patch))

            if patch == None:
                raise Exception(f"No patch found with id {id} in the db")

            patch_file = os.path.join(feedback_wd, str(feedback.patch))
            with open(patch_file, "w") as p:
                patch_content = str(patch.content)
                p.write(patch_content)

            context_file = os.path.join(feedback_wd, "context.md")
            with open(context_file, "w") as p:
                if patch.context == None:
                    context = ""
                else:
                    context = str(patch.context)
                p.write(context)
        archive = os.path.join(
            tempfile.mkdtemp(),
            f"user-feedback-{datetime.datetime.now().date()}-{int(datetime.datetime.now().timestamp())}",
        )
        shutil.make_archive(archive, "zip", wd, ".")
        archive_url = nexus.upload_file(
            f"{archive}.zip", os.path.basename(f"{archive}.zip")
        )
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[dataset_user_feedback] Exception {type(e)} occured during handling of task dataset user_feedback: {str(e)}",
        )
    else:
        return Response(archive=archive_url)
