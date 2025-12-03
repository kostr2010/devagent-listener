import base64
import zlib
import fastapi
import pydantic

from app.redis.async_redis import AsyncRedis
from app.db.async_db import AsyncDBSession
from app.db.schemas.user_feedback import UserFeedback
from app.routes.api.v1.devagent.tasks.validation import validate_query_params

from app.redis.schemas.task_info import (
    task_info_rules_revision_key,
    task_info_devagent_revision_key,
    task_info_patch_content_key,
    task_info_patch_context_key,
    task_info_project_revision_key,
)


class QueryParams(pydantic.BaseModel):
    task_id: str
    feedback: int
    data: str


class Response(pydantic.BaseModel):
    feedback_id: int


@validate_query_params(QueryParams)
async def action_set(
    db: AsyncDBSession, redis: AsyncRedis, query_params: QueryParams
) -> Response:
    try:
        project, file, line, rule = _decrypt_project_file_line_rule(query_params.data)

        task_info = await redis.get_task_info(query_params.task_id)

        if task_info == None:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Task info for task {query_params.task_id} expired or never existed",
            )

        ark_dev_rules_rev_key = task_info_rules_revision_key()
        ark_rev_rules_rev = task_info[ark_dev_rules_rev_key]

        devagent_rev_key = task_info_devagent_revision_key()
        devagent_rev = task_info[devagent_rev_key]

        project_rev_key = task_info_project_revision_key(project)
        project_rev = task_info[project_rev_key]

        patch_name = task_info[rule]

        patch_content_key = task_info_patch_content_key(patch_name)
        patch_content = task_info[patch_content_key]

        patch_context_key = task_info_patch_context_key(patch_name)
        patch_context = task_info[patch_context_key]

        await db.insert_patch_if_does_not_exist(
            patch_name, patch_content, patch_context
        )

        orm_feedback = UserFeedback(
            rev_arkcompiler_development_rules=ark_rev_rules_rev,
            rev_devagent=devagent_rev,
            project=project,
            rev_project=project_rev,
            patch=patch_name,
            rule=rule,
            file=file,
            line=int(line),
            feedback=query_params.feedback,
        )

        await db.insert_user_feebdack([orm_feedback])
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[user_feedback_set] Exception {type(e)} occured during handling of task {query_params.task_id}: {str(e)}",
        )
    else:
        return Response(feedback_id=orm_feedback.id)


###########
# private #
###########


def _encrypt_project_file_line_rule(
    project: str, file: str, line: str, rule: str
) -> str:
    data = f"{project}:{file}:{line}:{rule}"
    return base64.urlsafe_b64encode(zlib.compress(data.encode())).decode("utf-8")


def _decrypt_project_file_line_rule(data: str) -> tuple[str, str, str, str]:
    decrypted = zlib.decompress(base64.urlsafe_b64decode(data)).decode("utf-8")
    project, file, line, rule = decrypted.split(":")
    return project, file, line, rule
