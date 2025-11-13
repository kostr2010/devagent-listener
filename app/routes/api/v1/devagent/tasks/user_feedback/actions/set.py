import redis.asyncio
import sqlalchemy.ext.asyncio
import base64
import zlib
import fastapi
import pydantic
import typing

from app.postgres.models import UserFeedback
from app.postgres.infrastructure import save_patch_if_does_not_exist
from app.routes.api.v1.devagent.tasks.validation import validate_query_params
from app.routes.api.v1.devagent.tasks.task_info.actions.get import action_get
from app.redis.models import (
    task_info_patch_content_key,
    task_info_patch_context_key,
    task_info_project_revision_key,
)

QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "user_feedback_set query params schema",
    "description": "Query params schema of user_feedback_set API",
    "type": "object",
    "properties": {
        "task_id": {
            "description": "task_id of the devagent review",
            "type": "string",
        },
        "feedback": {
            "description": "User feedback for the alarm",
            "type": "string",
        },
        "data": {
            "description": "base64-encrypted and compressed project:file:line:rule",
            "type": "string",
        },
    },
    "required": ["task_id", "feedback", "data"],
    "additionalProperties": True,
}


class Response(pydantic.BaseModel):
    pass


@validate_query_params(QUERY_PARAMS_SCHEMA)
async def action_set(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    query_params: dict[str, typing.Any],
) -> Response:
    try:
        data = query_params["data"]
        project, file, line, rule = _decrypt_project_file_line_rule(data)

        task_info = await action_get(redis=redis, query_params=query_params)

        ark_dev_rules_project = "nazarovkonstantin/arkcompiler_development_rules"
        ark_dev_rules_rev_key = task_info_project_revision_key(ark_dev_rules_project)
        ark_rev_rules_rev = task_info[ark_dev_rules_rev_key]

        devagent_project = "egavrin/devagent"
        devagent_rev_key = task_info_project_revision_key(devagent_project)
        devagent_rev = task_info[devagent_rev_key]

        project_rev_key = task_info_project_revision_key(project)
        project_rev = task_info[project_rev_key]

        patch_name = task_info[rule]

        patch_content_key = task_info_patch_content_key(patch_name)
        patch_content = task_info[patch_content_key]

        patch_context_key = task_info_patch_context_key(patch_name)
        patch_context = task_info[patch_context_key]

        await save_patch_if_does_not_exist(
            postgres, patch_name, patch_content, patch_context
        )

        feedback = query_params["feedback"]

        orm_feedback = UserFeedback(
            rev_arkcompiler_development_rules=ark_rev_rules_rev,
            rev_devagent=devagent_rev,
            project=project,
            rev_project=project_rev,
            patch=patch_name,
            rule=rule,
            file=file,
            line=int(line),
            feedback=int(feedback),
        )

        postgres.add(orm_feedback)
        await postgres.commit()
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[user_feedback_set] Exception {type(e)} occured during handling of task {query_params['task_id']}: {str(e)}",
        )
    else:
        return Response()


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
