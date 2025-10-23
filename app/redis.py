import redis.asyncio

from .config import CONFIG


def init_async_redis_conn(db: str | int) -> redis.asyncio.Redis:
    return redis.asyncio.Redis(
        host=CONFIG.REDIS_HOST,
        port=CONFIG.REDIS_PORT,
        password=CONFIG.REDIS_PASSWORD,
        db=db,
    )
