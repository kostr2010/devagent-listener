import fastapi
import redis.asyncio


async def task_info_get(redis: redis.asyncio.Redis, payload: str | None) -> dict:
    _validate_payload(payload)

    res = await redis.hgetall(payload)

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
