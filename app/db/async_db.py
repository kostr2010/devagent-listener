import typing
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

    async def insert_patches(self, patches: list[Patch]) -> None:
        self._session.add_all(patches)
        await self._session.commit()

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


class SessionFactory:
    _engine: sqlalchemy.ext.asyncio.AsyncEngine
    _session_maker: sqlalchemy.ext.asyncio.async_sessionmaker[
        sqlalchemy.ext.asyncio.AsyncSession
    ]

    def __init__(self, url: str):
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

    async def get_session(self) -> typing.AsyncGenerator[AsyncSession, None]:
        async with self._session_maker() as session:
            try:
                yield AsyncSession(session)
            except Exception as e:
                await session.rollback()
                raise RuntimeError(
                    f"[get_session] Exception {type(e)} occured : {str(e)}",
                )
