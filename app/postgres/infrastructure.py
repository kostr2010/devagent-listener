import sqlalchemy.ext.asyncio
import sqlalchemy.future

from app.postgres.models import Patch


async def save_patch_if_does_not_exist(
    postgres: sqlalchemy.ext.asyncio.AsyncSession, id: str, content: str
) -> None:
    query_res = await postgres.execute(
        sqlalchemy.future.select(Patch).where(Patch.id == id)
    )
    existing_patch = query_res.scalars().first()

    if existing_patch != None:
        return

    new_patch = Patch(id=id, content=content)

    postgres.add(new_patch)

    await postgres.commit()
