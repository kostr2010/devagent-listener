import redis.asyncio
import sqlalchemy.ext.asyncio
import base64
import zlib
import fastapi

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
            "type": "string",
        },
        "feedback": {
            "description": "User feedback for the alarm",
            "type": "string",
        },
        "data": {
            "description": "base64-encrypted and compressed repo:file:line:rule",
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
    "properties": {},
    "required": [],
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
        feedback = query_params["feedback"]
        data = query_params["data"]

        repo, file, line, rule = _decrypt_file_line_rule(data)

        task_info = await task_info_get(redis=redis, query_params=query_params)

        rev_arkcompiler_development_rules = task_info[
            "rev_arkcompiler_development_rules"
        ]
        rev_devagent = task_info["rev_devagent"]
        repo = repo
        rev = task_info[f"rev_{repo}"]
        patch = task_info[rule]
        content = task_info[patch]

        await save_patch_if_does_not_exist(postgres, patch, content)

        orm_feedback = UserFeedback(
            rev_arkcompiler_development_rules=rev_arkcompiler_development_rules,
            rev_devagent=rev_devagent,
            repo=repo,
            rev=rev,
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
            detail=f"[user_feedback_set] Exception occured during handling of task {query_params['task_id']}: {str(e)}",
        )
    else:
        return {}


###########
# private #
###########


def _encrypt_file_line_rule(repo: str, file: str, line: str, rule: str) -> str:
    data = f"{repo}:{file}:{line}:{rule}"
    return base64.urlsafe_b64encode(zlib.compress(data.encode())).decode("utf-8")


def _decrypt_file_line_rule(data: str) -> tuple[str, str, str, str]:
    decrypted = zlib.decompress(base64.urlsafe_b64decode(data)).decode("utf-8")
    repo, file, line, rule = decrypted.split(":")
    return repo, file, line, rule
