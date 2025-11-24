import fastapi
import contextlib
import redis.asyncio
import typing

from app.config import CONFIG
from app.redis.redis import init_async_redis_conn
from app.db.async_db import AsyncConnection, AsyncSession
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
    print("Initializing db connection")
    app.state.async_db_conn = AsyncConnection(
        CONFIG.DB_PROTOCOL,
        CONFIG.DB_HOSTNAME,
        CONFIG.DB_PORT,
        CONFIG.DB_USER,
        CONFIG.DB_PASSWORD,
        CONFIG.DB_DB,
    )
    print("Running db migrations")
    await app.state.async_db_conn.run_migrations()
    print("Listening for requests")
    yield
    print("Closing redis connection")
    await app.state.async_redis_conn.close()
    print("Closing db connection")
    await app.state.async_db_conn.close()


def get_redis_connection(request: fastapi.Request) -> redis.asyncio.Redis:
    conn: redis.asyncio.Redis = request.app.state.async_redis_conn
    return conn


async def get_db_session(
    request: fastapi.Request,
) -> typing.AsyncGenerator[AsyncSession, None]:
    conn: AsyncConnection = request.app.state.async_db_conn
    async for session in conn.get_session():
        yield session


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
    db: typing.Annotated[AsyncSession, fastapi.Depends(get_db_session)],
    redis: typing.Annotated[redis.asyncio.Redis, fastapi.Depends(get_redis_connection)],
) -> ResponseApiV1Devagent:
    """Entrypoint for the devagent related logic

    Args:
        response (fastapi.Response): response
        request (fastapi.Request): request
        task_kind (typing.Annotated[int, fastapi.Query()]): task that needs to be performed by the endpoint
        action (typing.Annotated[int, fastapi.Query()]): action that needs to be performed for the task
        postgres (typing.Annotated[AsyncSession, fastapi.Depends(get_db_session)]): db connection
        redis (typing.Annotated[redis.asyncio.Redis, fastapi.Depends(get_redis_connection)): redis connection

    Returns:
        ResponseApiV1Devagent: response. depends on the task_kind and action provided
    """

    if not authenticate_request(request):
        raise fastapi.HTTPException(status_code=400, detail="Authentication failed")

    return await endpoint_api_v1_devagent(
        response=response,
        request=request,
        db=db,
        redis=redis,
        task_kind=task_kind,
        action=action,
    )
