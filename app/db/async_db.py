import typing
import alembic.config
import alembic.command
import sqlalchemy.future
import sqlalchemy.ext.asyncio

from app.db.schemas.error import Error
from app.db.schemas.patch import Patch
from app.db.schemas.user_feedback import UserFeedback


ColumnSelector = typing.Callable[[], typing.Any]


class AsyncSession:
    _session: sqlalchemy.ext.asyncio.AsyncSession

    def __init__(self, session: sqlalchemy.ext.asyncio.AsyncSession):
        self._session = session

    async def select_errors(self, selector: ColumnSelector | None) -> list[Error]:
        select = sqlalchemy.future.select(Error)
        if selector:
            select = select.where(selector)
        query_res = await self._session.execute(select)
        return [res for res in query_res.scalars().all()]

    async def insert_errors(self, errors: list[Error]) -> None:
        self._session.add_all(errors)
        await self._session.commit()

    async def select_patches(self, selector: ColumnSelector | None) -> list[Patch]:
        select = sqlalchemy.future.select(Patch)
        if selector:
            select = select.where(selector)
        query_res = await self._session.execute(select)
        return [res for res in query_res.scalars().all()]

    async def get_patch(self, id: str) -> Patch | None:
        patches = await self.select_patches(lambda: Patch.id == id)

        if len(patches) == 0:
            return None

        if len(patches) > 1:
            raise Exception(f"Multiple patches matched {id} in the db")

        return patches[0]

    async def insert_patches(self, patches: list[Patch]) -> None:
        self._session.add_all(patches)
        await self._session.commit()

    async def insert_patch_if_does_not_exist(
        self,
        id: str,
        content: str,
        context: str | None,
    ) -> None:
        existing_patch = await self.get_patch(id)

        if existing_patch != None:
            return

        await self.insert_patches([Patch(id=id, content=content, context=context)])

    async def select_user_feebdack(
        self, selector: ColumnSelector | None
    ) -> list[UserFeedback]:
        select = sqlalchemy.future.select(UserFeedback)
        if selector:
            select = select.where(selector)
        query_res = await self._session.execute(select)
        return [res for res in query_res.scalars().all()]

    async def insert_user_feebdack(self, user_feedback: list[UserFeedback]) -> None:
        self._session.add_all(user_feedback)
        await self._session.commit()


class AsyncConnection:
    _engine: sqlalchemy.ext.asyncio.AsyncEngine
    _session_maker: sqlalchemy.ext.asyncio.async_sessionmaker[
        sqlalchemy.ext.asyncio.AsyncSession
    ]

    def __init__(
        self, protocol: str, host: str, port: int, user: str, pwd: str, db: str
    ):
        url = f"{protocol}://{user}:{pwd}@{host}:{port}/{db}"
        self._engine = sqlalchemy.ext.asyncio.create_async_engine(
            url, echo=True, future=True, pool_size=100, max_overflow=20
        )
        self._session_maker = sqlalchemy.ext.asyncio.async_sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
            class_=sqlalchemy.ext.asyncio.AsyncSession,
        )

    async def close(self) -> None:
        await self._engine.dispose()

    async def run_migrations(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(_run_migrations)

    async def get_session(self) -> typing.AsyncGenerator[AsyncSession, None]:
        async with self._session_maker() as session:
            try:
                yield AsyncSession(session)
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise RuntimeError(
                    f"[get_session] Exception {type(e)} occured : {str(e)}",
                )


###########
# private #
###########


def _run_migrations(conn: sqlalchemy.Connection) -> None:
    cfg = alembic.config.Config("alembic.ini")
    cfg.attributes["connection"] = conn
    alembic.command.upgrade(cfg, "head")
