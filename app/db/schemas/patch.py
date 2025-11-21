import sqlalchemy
import sqlalchemy.ext.declarative


class Patch(sqlalchemy.ext.declarative.declarative_base()):  # type: ignore
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
