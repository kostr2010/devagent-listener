import sqlalchemy.orm
import sqlalchemy.ext.asyncio

from .config import app_settings

PG_USER = app_settings.POSTGRES_USER
PG_PASS = app_settings.POSTGRES_PASSWORD
PG_HOST = app_settings.POSTGRES_HOSTNAME
PG_PORT = app_settings.DATABASE_PORT
PG_DB = app_settings.POSTGRES_DB
PG_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"

SQL_ENGINE = sqlalchemy.ext.asyncio.create_async_engine(
    PG_URL, echo=True, future=True, pool_size=100, max_overflow=20
)

SQL_SESSION = sqlalchemy.ext.asyncio.async_sessionmaker(
    bind=SQL_ENGINE,
    autoflush=False,
    expire_on_commit=False,
)
