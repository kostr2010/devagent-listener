import fastapi
import contextlib
import redis.asyncio
import alembic.config
import sqlalchemy.ext.asyncio
import typing

from .postgres.database import SQL_SESSION, SQL_ENGINE
from .redis.redis import init_async_redis_conn
from .config import CONFIG

from .api.v1.devagent.endpoint import api_v1_devagent_endpoint


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    print("Initializing redis connection")
    app.state.async_redis_conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)
    print("Running postgres migrations")
    await run_async_postgres_migrations()
    print("Listening")
    yield
    print("Closing redis connection")
    await app.state.async_redis_conn.close()


def get_redis(request: fastapi.Request):
    return request.app.state.async_redis_conn


async def get_postgres():
    async with SQL_SESSION() as session:
        yield session
        await session.commit()


def run_postgres_migrations(connection):
    cfg = alembic.config.Config("alembic.ini")
    cfg.attributes["connection"] = connection
    alembic.command.upgrade(cfg, "head")


async def run_async_postgres_migrations():
    async with SQL_ENGINE.begin() as conn:
        await conn.run_sync(run_postgres_migrations)


listener = fastapi.FastAPI(debug=True, lifespan=lifespan)


@listener.get("/health")
def health_endpoint():
    return {"status": "healthy"}


@listener.get("/api/v1/devagent")
async def devagent_endpoint(
    response: fastapi.Response,
    request: fastapi.Request,
    task_kind: typing.Annotated[int, fastapi.Query()],
    action: typing.Annotated[int, fastapi.Query()],
    postgres: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(get_postgres),
    redis: redis.asyncio.Redis = fastapi.Depends(get_redis),
) -> dict:
    """Entrypoint for the devagent related logic

    Args:
        response (fastapi.Response): response
        request (fastapi.Request): request
        task_kind (typing.Annotated[int, fastapi.Query): task that needs to be performed by the endpoint
        action (typing.Annotated[int, fastapi.Query): action that needs to be performed for the task
        postgres (sqlalchemy.ext.asyncio.AsyncSession, optional): postgres connection. Defaults to fastapi.Depends(get_postgres).
        redis (redis.asyncio.Redis, optional): redis connection. Defaults to fastapi.Depends(get_redis).

    Returns:
        dict: response. depends on the task_kind and action provided
    """
    # TODO: add secret key validation

    return await api_v1_devagent_endpoint(
        response=response,
        request=request,
        postgres=postgres,
        redis=redis,
        task_kind=task_kind,
        action=action,
    )
