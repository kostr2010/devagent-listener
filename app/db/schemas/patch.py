import sqlalchemy

from app.db.schemas.base import SQL_BASE


class Patch(SQL_BASE):  # type: ignore
    __tablename__ = "patches"

    id = sqlalchemy.Column(
        sqlalchemy.String,
        primary_key=True,
        nullable=False,
        unique=True,
        autoincrement=False,
    )
    content = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    context = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_at = sqlalchemy.Column(
        sqlalchemy.DateTime, default=sqlalchemy.sql.func.now(), nullable=True
    )
    updated_at = sqlalchemy.Column(
        sqlalchemy.DateTime,
        default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
        nullable=True,
    )
