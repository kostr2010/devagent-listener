import fastapi
import json
import jsonschema

PAYLOAD_SCHEMA_JSON = "payload.schema.json"
RESPONSE_SCHEMA_JSON = "response.schema.json"


def validate_payload(payload: str | None, allow_empty_payload: bool = False) -> None:
    if payload == None:
        if allow_empty_payload:
            return
        raise fastapi.HTTPException(
            status_code=400,
            detail=f"Expected non-empty value for payload",
        )

    payload_schema = None
    try:
        file = open(PAYLOAD_SCHEMA_JSON)
        content = file.read()
        file.close()
        payload_schema = json.loads(content)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500, detail=f"Error while reading payload schema : {str(e)}"
        )

    parsed_payload = None
    try:
        parsed_payload = json.loads(payload)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=f"Error while parsing payload : {str(e)}"
        )

    try:
        jsonschema.validate(parsed_payload, payload_schema)
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=f"Error while validating payload : {str(e)}"
        )
