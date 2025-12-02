import fastapi
import contextlib
import typing

from app.config import CONFIG
from app.utils.authentication import generate_signature
from app.diff.provider import DiffProvider
from app.diff.providers.gitcode_provider import GitcodeDiffProvider
from app.nexus.repo import NexusRepo
from app.redis.async_redis import AsyncRedis, AsyncRedisConfig
from app.db.async_db import AsyncDBConnection, AsyncDBConnectionConfig, AsyncDBSession

from app.routes.api.v1.devagent.endpoint import (
    endpoint_api_v1_devagent,
    Response as ResponseApiV1Devagent,
)
from app.routes.health.endpoint import (
    endpoint_health,
    Response as ResponseHealth,
)


def authenticate_request(request: fastapi.Request) -> bool:
    """Check if request has valid credentials

    Args:
        request (fastapi.Request): request

    Returns:
        bool: Whether request is authenticated or not
    """

    header_timestamp = request.headers.get("timestamp")
    header_signature = request.headers.get("sign")

    if not header_timestamp or not header_signature:
        return False

    generated_signature = generate_signature(header_timestamp, CONFIG.SECRET_KEY)

    return header_signature == generated_signature


def get_redis_connection(request: fastapi.Request) -> AsyncRedis:
    redis: AsyncRedis = request.app.state.async_redis
    return redis


async def get_db_session(
    request: fastapi.Request,
) -> typing.AsyncGenerator[AsyncDBSession, None]:
    db: AsyncDBConnection = request.app.state.async_db
    async for session in db.get_session():
        yield session


def get_nexus_repo(request: fastapi.Request) -> NexusRepo:
    nexus: NexusRepo = request.app.state.nexus_repo
    return nexus


def get_diff_provider(request: fastapi.Request) -> DiffProvider:
    diff_provider: DiffProvider = request.app.state.diff_provider
    return diff_provider


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):  # type: ignore
    print("Initializing diff providers")
    diff_provider = DiffProvider()
    gitcode_provider = GitcodeDiffProvider(CONFIG.GITCODE_TOKEN)
    diff_provider.register_provider(gitcode_provider)
    app.state.diff_provider = diff_provider
    print("Initializing nexus repo")
    app.state.nexus_repo = NexusRepo(
        username=CONFIG.NEXUS_USERNAME,
        password=CONFIG.NEXUS_PASSWORD,
        repo=CONFIG.NEXUS_REPO_URL,
    )
    print("Initializing redis connection")
    async_redis_cfg = AsyncRedisConfig(
        host=CONFIG.REDIS_HOST,
        port=CONFIG.REDIS_PORT,
        password=CONFIG.REDIS_PASSWORD,
        db=CONFIG.REDIS_LISTENER_DB,
        expiry=CONFIG.EXPIRY_TASK_INFO,
    )
    app.state.async_redis = AsyncRedis(async_redis_cfg)
    print("Initializing db connection")
    async_db_cfg = AsyncDBConnectionConfig(
        protocol=CONFIG.DB_PROTOCOL,
        host=CONFIG.DB_HOSTNAME,
        port=CONFIG.DB_PORT,
        user=CONFIG.DB_USER,
        password=CONFIG.DB_PASSWORD,
        db=CONFIG.DB_DB,
    )
    app.state.async_db = AsyncDBConnection(async_db_cfg)
    print("Running db migrations")
    await app.state.async_db.run_migrations()
    print("Listening for requests")
    yield
    print("Closing redis connection")
    await app.state.async_redis.close()
    print("Closing db connection")
    await app.state.async_db.close()


listener = fastapi.FastAPI(debug=True, lifespan=lifespan)


@listener.get("/health")
def health(request: fastapi.Request) -> ResponseHealth:
    """Basic healthcheck endpoint

    Returns:
        ResponseHealth: response with the 'healthy' status
    """

    if not authenticate_request(request):
        raise fastapi.HTTPException(status_code=400, detail="Authentication failed")

    return endpoint_health()


@listener.get("/api/v1/devagent")
async def api_v1_devagent(
    request: fastapi.Request,
    task_kind: typing.Annotated[int, fastapi.Query()],
    action: typing.Annotated[int, fastapi.Query()],
    db: typing.Annotated[AsyncDBSession, fastapi.Depends(get_db_session)],
    redis: typing.Annotated[AsyncRedis, fastapi.Depends(get_redis_connection)],
    nexus: typing.Annotated[NexusRepo, fastapi.Depends(get_nexus_repo)],
    diff_provider: typing.Annotated[DiffProvider, fastapi.Depends(get_diff_provider)],
) -> ResponseApiV1Devagent:
    """Entrypoint for the devagent related logic

    Args:
        response (fastapi.Response): response
        request (fastapi.Request): request
        task_kind (typing.Annotated[int, fastapi.Query()]): task that needs to be performed by the endpoint
        action (typing.Annotated[int, fastapi.Query()]): action that needs to be performed for the task
        postgres (typing.Annotated[AsyncDBSession, fastapi.Depends(get_db_session)]): db connection
        redis (typing.Annotated[AsyncRedis, fastapi.Depends(get_redis_connection)]): redis connection
        nexus (typing.Annotated[NexusRepo, fastapi.Depends(get_nexus_repo)]): nexus repo wrapper
        diff_provider (typing.Annotated[DiffProvider, fastapi.Depends(get_diff_provider)]): unified interface to obtain git diff

    Returns:
        ResponseApiV1Devagent: response. depends on the task_kind and action provided
    """

    if not authenticate_request(request):
        raise fastapi.HTTPException(status_code=400, detail="Authentication failed")

    return await endpoint_api_v1_devagent(
        request=request,
        db=db,
        redis=redis,
        nexus=nexus,
        diff_provider=diff_provider,
        task_kind=task_kind,
        action=action,
    )
