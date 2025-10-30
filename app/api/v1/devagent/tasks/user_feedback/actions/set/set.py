import redis.asyncio
import sqlalchemy.ext.asyncio
import fastapi
import json
import jsonschema

from app.postgres.models import UserFeedback
from app.postgres.infrastructure import save_patch_if_does_not_exist


from app.api.v1.devagent.infrastructure import RESPONSE_SCHEMA_JSON, PAYLOAD_SCHEMA_JSON

async def user_feedback_set(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    payload: str | None,
) -> dict:
    _validate_payload(payload)

    content = json.loads(payload)

    result = {}

    orm_user_feedback = []

    for task_id, user_feebdack_list in content.items():
        task_info = await redis.hgetall(task_id)

        if task_info == None or len(task_info.keys()) == 0:
            result.update(
                {task_id: {"code": -1, "message": "Task info expired or never existed"}}
            )
            continue

        rev_arkcompiler_development_rules = task_info[
            "rev_arkcompiler_development_rules"
        ]
        rev_devagent = task_info["rev_devagent"]

        for user_feedback in user_feebdack_list:
            feedback = user_feedback["feedback"]
            rule = user_feedback["rule"]
            file = user_feedback["file"]
            line = user_feedback["line"]

            patch = task_info[rule]
            content = task_info[patch]

            await save_patch_if_does_not_exist(patch, content)

            orm_feedback = UserFeedback(
                rev_arkcompiler_development_rules=rev_arkcompiler_development_rules,
                rev_devagent=rev_devagent,
                patch=patch,
                rule=rule,
                file=file,
                line=line,
                feedback=feedback,
            )

            orm_user_feedback.append(orm_feedback)

    postgres.add_all(orm_user_feedback)
    await postgres.commit()

    return result


###########
# private #
###########


def _validate_payload(
    payload: str | None,
) -> None:
    if payload == None:
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for payload",
        )
    # FIXME: rewrite to infrastructure.py
    with open()
    schema = json.loads()
    content = json.loads(payload)
    jsonschema.validate(content, PAYLOAD_SCHEMA)
