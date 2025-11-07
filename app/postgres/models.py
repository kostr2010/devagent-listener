import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import enum

SQL_BASE = sqlalchemy.ext.declarative.declarative_base()


class Feedback(enum.IntEnum):
    TRUE_POSITIVE = 0
    FALSE_POSITIVE = 1
    TRUE_NEGATIE = 2
    FALSE_NEGATIE = 3


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


class UserFeedback(SQL_BASE):  # type: ignore
    __tablename__ = "user_feedback"

    id = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, nullable=False, unique=True
    )
    rev_arkcompiler_development_rules = sqlalchemy.Column(
        sqlalchemy.String, nullable=False
    )
    rev_devagent = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    rev_project = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    patch = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    rule = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    file = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    line = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    feedback = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)

    @sqlalchemy.orm.validates("feedback")
    def validate_feedback(self, key: str, value: int) -> int:
        if not value in [e.value for e in Feedback]:
            raise ValueError(f"Invalid feedback value {value} for key {key}")
        return value


class Error(SQL_BASE):  # type: ignore
    __tablename__ = "errors"

    id = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, nullable=False, unique=True
    )
    rev_arkcompiler_development_rules = sqlalchemy.Column(
        sqlalchemy.String, nullable=False
    )
    rev_devagent = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    project = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    rev_project = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    patch = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    rule = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    message = sqlalchemy.Column(sqlalchemy.String, nullable=False)
