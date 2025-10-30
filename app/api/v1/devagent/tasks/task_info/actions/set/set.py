import fastapi
import redis.asyncio

import json
import jsonschema

from app.config import CONFIG

PAYLOAD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Task Info",
    "description": "Payload schema of task_info_set API",
    "type": "object",
    "patternProperties": {
        "^.*$": {
            "description": "Task id of the review",
            "type": "object",
            "properties": {
                "rev_arkcompiler_development_rules": {
                    "description": "Revision of the arkcompiler_development_rules repository used for review",
                    "type": "string",
                },
                "rev_devagent": {
                    "description": "Revision of the devagent repository used for review",
                    "type": "string",
                },
            },
            "patternProperties": {
                "^.*.patch$": {
                    "description": "Patch name mapped to the content",
                    "type": "string",
                },
                "^ETS.*.md$": {
                    "description": "Rule name mapped to the patch name",
                    "type": "string",
                },
                # TODO: expand when new rules are added
            },
            "required": ["rev_arkcompiler_development_rules", "rev_devagent"],
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


async def task_info_set(redis: redis.asyncio.Redis, payload: str | None) -> dict:
    _validate_payload(payload)

    info = json.loads(payload)

    res = {}
    for task, info in info.items():
        vals_written = await redis.hsetex(
            name=task, mapping=info, ex=CONFIG.EXPIRY_TASK_INFO
        )
        res.update({task: vals_written})

    return res


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
    content = json.loads(payload)
    jsonschema.validate(content, PAYLOAD_SCHEMA)
