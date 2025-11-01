import redis.asyncio
import sqlalchemy.ext.asyncio
import base64
import zlib

from app.postgres.models import UserFeedback
from app.postgres.infrastructure import save_patch_if_does_not_exist
from app.utils.validation import validate_result
from app.api.v1.devagent.infrastructure import validate_query_params
from app.api.v1.devagent.tasks.task_info.actions.get import task_info_get

QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "user_feedback_set query params schema",
    "description": "Query params schema of user_feedback_set API",
    "type": "object",
    "properties": {
        "task_id": {
            "description": "task_id of the devagent review",
            "type": "boolean",
        },
        "feedback": {
            "description": "User feedback for the alarm",
            "type": "boolean",
        },
        "data": {
            "description": "base64-encrypted and compressed file:line:rule",
            "type": "string",
        },
    },
    "required": ["task_id", "feedback", "data"],
    "additionalProperties": True,
}

RESPONSE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "user_feedback_set response shema",
    "description": "Response schema of user_feedback_set API",
    "type": "object",
    "properties": {
        "successfull": {
            "description": "Whether feedback was stored successfully",
            "type": "boolean",
        },
        "message": {
            "description": "Message in case of failure",
            "type": "string",
        },
    },
    "required": ["task_id", "successfull"],
    "additionalProperties": False,
}


@validate_result(RESPONSE_SCHEMA)
@validate_query_params(QUERY_PARAMS_SCHEMA)
async def user_feedback_set(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    query_params: dict,
) -> dict:
    try:
        task_id: str = query_params["task_id"]
        feedback: bool = query_params["feedback"]
        data: str = query_params["data"]

        file, line, rule = _decrypt_file_line_rule(data)

        task_info = await task_info_get(redis=redis, query_params=query_params)

        rev_arkcompiler_development_rules = task_info[
            "rev_arkcompiler_development_rules"
        ]
        rev_arkcompiler_runtime_core = task_info["rev_arkcompiler_runtime_core"]
        rev_arkcompiler_ets_frontend = task_info["rev_arkcompiler_ets_frontend"]
        rev_devagent = task_info["rev_devagent"]
        patch = task_info[rule]
        content = task_info[patch]

        await save_patch_if_does_not_exist(patch, content)

        orm_feedback = UserFeedback(
            rev_arkcompiler_development_rules=rev_arkcompiler_development_rules,
            rev_arkcompiler_runtime_core=rev_arkcompiler_runtime_core,
            rev_arkcompiler_ets_frontend=rev_arkcompiler_ets_frontend,
            rev_devagent=rev_devagent,
            patch=patch,
            rule=rule,
            file=file,
            line=line,
            feedback=feedback,
        )

        postgres.add(orm_feedback)
        await postgres.commit()
    except Exception as e:
        return {
            "successfull": False,
            "message": f"[user_feedback_set] Exception occured during handling of task {task_id}: {str(e)}",
        }
    else:
        return {
            "successfull": True,
        }


###########
# private #
###########


def _encrypt_file_line_rule(file: str, line: str, rule: str) -> str:
    data = f"{file}:{line}:{rule}"
    return base64.urlsafe_b64encode(zlib.compress(data.encode()))


def _decrypt_file_line_rule(data: str) -> tuple[str, str, str]:
    zlib.decompress(base64.urlsafe_b64decode(data))
    file, line, rule = data.split(":")
    return file, line, rule
