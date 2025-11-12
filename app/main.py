import fastapi
import contextlib
import redis.asyncio
import alembic.config
import sqlalchemy.ext.asyncio
import typing

from app.postgres.database import SQL_SESSION, SQL_ENGINE
from app.redis.redis import init_async_redis_conn
from app.config import CONFIG
from app.auth.authentication import authenticate_request

from app.routes.api.v1.devagent.endpoint import (
    endpoint_api_v1_devagent,
    Response as ResponseApiV1Devagent,
)
from app.routes.health.endpoint import (
    endpoint_health,
    Response as ResponseHealth,
)


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):  # type: ignore
    print("Initializing redis connection")
    app.state.async_redis_conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)
    print("Running postgres migrations")
    await run_async_postgres_migrations()
    print("Listening")
    yield
    print("Closing redis connection")
    await app.state.async_redis_conn.close()


def get_redis(request: fastapi.Request) -> redis.asyncio.Redis:
    conn: redis.asyncio.Redis = request.app.state.async_redis_conn
    return conn


async def get_postgres():  # type: ignore
    async with SQL_SESSION() as session:
        yield session
        await session.commit()


def run_postgres_migrations(connection: sqlalchemy.Connection) -> None:
    cfg = alembic.config.Config("alembic.ini")
    cfg.attributes["connection"] = connection
    alembic.command.upgrade(cfg, "head")


async def run_async_postgres_migrations() -> None:
    async with SQL_ENGINE.begin() as conn:
        await conn.run_sync(run_postgres_migrations)


listener = fastapi.FastAPI(debug=True, lifespan=lifespan)


@listener.get("/health")
def health(response: fastapi.Response, request: fastapi.Request) -> ResponseHealth:
    """Basic healthcheck endpoint

    Returns:
        ResponseHealth: response with the 'healthy' status
    """

    if not authenticate_request(request):
        raise fastapi.HTTPException(status_code=400, detail="Authentication failed")

    return endpoint_health()


@listener.get("/api/v1/devagent")
async def api_v1_devagent(
    response: fastapi.Response,
    request: fastapi.Request,
    task_kind: typing.Annotated[int, fastapi.Query()],
    action: typing.Annotated[int, fastapi.Query()],
    postgres: sqlalchemy.ext.asyncio.AsyncSession = fastapi.Depends(get_postgres),
    redis: redis.asyncio.Redis = fastapi.Depends(get_redis),
) -> ResponseApiV1Devagent:
    """Entrypoint for the devagent related logic

    Args:
        response (fastapi.Response): response
        request (fastapi.Request): request
        task_kind (typing.Annotated[int, fastapi.Query): task that needs to be performed by the endpoint
        action (typing.Annotated[int, fastapi.Query): action that needs to be performed for the task
        postgres (sqlalchemy.ext.asyncio.AsyncSession, optional): postgres connection. Defaults to fastapi.Depends(get_postgres).
        redis (redis.asyncio.Redis, optional): redis connection. Defaults to fastapi.Depends(get_redis).

    Returns:
        ResponseApiV1Devagent: response. depends on the task_kind and action provided
    """

    # if not authenticate_request(request):
    #     raise fastapi.HTTPException(status_code=400, detail="Authentication failed")

    return await endpoint_api_v1_devagent(
        response=response,
        request=request,
        postgres=postgres,
        redis=redis,
        task_kind=task_kind,
        action=action,
    )
