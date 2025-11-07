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
        feedback = query_params["feedback"]
        data = query_params["data"]

        project, file, line, rule = _decrypt_project_file_line_rule(data)

        task_info = await action_get(redis=redis, query_params=query_params)

        rev_arkcompiler_development_rules = task_info[
            "rev_nazarovkonstantin/arkcompiler_development_rules"
        ]
        rev_devagent = task_info["rev_egavrin/devagent"]
        rev_project = task_info[f"rev_{project}"]
        patch = task_info[rule]
        content = task_info[patch]

        await save_patch_if_does_not_exist(postgres, patch, content)

        orm_feedback = UserFeedback(
            rev_arkcompiler_development_rules=rev_arkcompiler_development_rules,
            rev_devagent=rev_devagent,
            project=project,
            rev_project=rev_project,
            patch=patch,
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
