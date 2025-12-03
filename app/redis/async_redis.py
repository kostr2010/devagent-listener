import redis.asyncio
import jsonschema
import pydantic

from app.redis.schemas.task_info import TASK_INFO_SCHEMA


class AsyncRedisConfig(pydantic.BaseModel):
    host: str
    port: int
    password: str
    db: int
    expiry: int


class AsyncRedis:
    _conf: AsyncRedisConfig
    _conn: redis.asyncio.Redis

    def __init__(self, cfg: AsyncRedisConfig):
        self._conn = redis.asyncio.Redis(
            host=cfg.host,
            port=cfg.port,
            password=cfg.password,
            db=cfg.db,
        )
        self._conf = cfg

    def config(self) -> AsyncRedisConfig:
        return self._conf

    async def set_task_info(
        self, task_info: dict[str, str], expiry: int | None = None
    ) -> None:
        jsonschema.validate(task_info, TASK_INFO_SCHEMA)

        task_id = str(task_info["task_id"])
        task_info = dict((k, str(v)) for k, v in task_info.items())

        # since async redis is used, it is always Awaitable
        vals_written = await self._conn.hsetex(
            name=task_id, mapping=task_info, ex=(expiry or self._conf.expiry)
        )  # type: ignore

        assert vals_written == 1

    async def get_task_info(self, task_id: str) -> dict[str, str] | None:
        # since async redis is used, it is always Awaitable
        task_info = await self._conn.hgetall(task_id)  # type: ignore

        if len(task_info.keys()) == 0:
            # task_info expired or never existed
            return None

        decoded = dict(
            (k.decode("utf-8"), v.decode("utf-8")) for k, v in task_info.items()
        )

        jsonschema.validate(decoded, TASK_INFO_SCHEMA)

        return decoded

    async def close(self) -> None:
        await self._conn.close()
