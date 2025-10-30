import fastapi
import redis.asyncio
import sqlalchemy.ext.asyncio

import json
import jsonschema

PAYLOAD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "User feedback",
    "description": "Payload schema of user_feedback_set API",
    "type": "object",
    "patternProperties": {
        "^.*$": {
            "description": "Task id of the review",
            "type": "object",
            "properties": {
                "feedback": {
                    "description": "User feedback for the devagent alarm",
                    "type": "boolean",
                },
                "rule": {
                    "description": "Name of the rule that was reported",
                    "type": "string",
                },
                "file": {
                    "description": "Name of the file that was reported",
                    "type": "string",
                },
                "line": {
                    "description": "Line number that was reported",
                    "type": "string",
                },
            },
            "required": ["feedback", "rule", "file", "line"],
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


def user_feedback_set(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
    payload: str | None,
) -> dict:
    _validate_payload(payload)

    # FIXME: implement

    return {}


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
