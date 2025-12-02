import typing
import alembic.config
import alembic.command
import sqlalchemy.future
import sqlalchemy.ext.asyncio
import pydantic

from app.db.schemas.error import Error
from app.db.schemas.patch import Patch
from app.db.schemas.user_feedback import UserFeedback


ColumnSelector = typing.Callable[[], typing.Any]


class AsyncDBConnectionConfig(pydantic.BaseModel):
    protocol: str
    host: str
    port: int
    user: str
    password: str
    db: str


class AsyncDBSession:
    _conf: AsyncDBConnectionConfig
    _session: sqlalchemy.ext.asyncio.AsyncSession

    def __init__(
        self, session: sqlalchemy.ext.asyncio.AsyncSession, cfg: AsyncDBConnectionConfig
    ):
        self._conf = cfg
        self._session = session

    def config(self) -> AsyncDBConnectionConfig:
        return self._conf

    async def select_errors(self, selector: ColumnSelector | None) -> list[Error]:
        select = sqlalchemy.future.select(Error)
        if selector:
            select = select.where(selector)
        query_res = await self._session.execute(select)
        return [res for res in query_res.scalars().all()]

    async def insert_errors(self, errors: list[Error]) -> None:
        self._session.add_all(errors)
        await self._session.commit()
        for item in errors:
            await self._session.refresh(item)

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
        for item in patches:
            await self._session.refresh(item)

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

    async def get_user_feebdack(self, id: int) -> UserFeedback | None:
        feedback = await self.select_user_feebdack(lambda: UserFeedback.id == id)
        if len(feedback) == 0:
            return None
        if len(feedback) > 1:
            raise Exception(f"Multiple feedbacks matched {id} in the db")
        return feedback[0]

    async def insert_user_feebdack(self, user_feedback: list[UserFeedback]) -> None:
        self._session.add_all(user_feedback)
        await self._session.commit()
        for item in user_feedback:
            await self._session.refresh(item)

    async def update_user_feebdack(self, id: int, new_feedback: int) -> None:
        await self._session.execute(
            sqlalchemy.update(UserFeedback)
            .where(UserFeedback.id == id)
            .values(feedback=new_feedback)
        )

    async def commit(self) -> None:
        await self._session.commit()


class AsyncDBConnection:
    _conf: AsyncDBConnectionConfig
    _engine: sqlalchemy.ext.asyncio.AsyncEngine
    _session_maker: sqlalchemy.ext.asyncio.async_sessionmaker[
        sqlalchemy.ext.asyncio.AsyncSession
    ]

    def __init__(self, cfg: AsyncDBConnectionConfig):
        url = (
            f"{cfg.protocol}://{cfg.user}:{cfg.password}@{cfg.host}:{cfg.port}/{cfg.db}"
        )
        self._conf = cfg
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

    async def get_session(self) -> typing.AsyncGenerator[AsyncDBSession, None]:
        async with self._session_maker() as session:
            try:
                yield AsyncDBSession(session, self._conf)
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
