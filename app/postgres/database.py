import sqlalchemy.ext.asyncio

from app.config import CONFIG

PG_USER = CONFIG.POSTGRES_USER
PG_PASS = CONFIG.POSTGRES_PASSWORD
PG_HOST = CONFIG.POSTGRES_HOSTNAME
PG_PORT = CONFIG.POSTGRES_PORT
PG_DB = CONFIG.POSTGRES_DB
PG_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"

SQL_ENGINE = sqlalchemy.ext.asyncio.create_async_engine(
    PG_URL, echo=True, future=True, pool_size=100, max_overflow=20
)

SQL_SESSION = sqlalchemy.ext.asyncio.async_sessionmaker(
    bind=SQL_ENGINE,
    autoflush=False,
    expire_on_commit=False,
)
