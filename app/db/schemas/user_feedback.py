import sqlalchemy
import enum

from app.db.schemas.base import SQL_BASE


class Feedback(enum.IntEnum):
    FALSE_POSITIVE = 0
    TRUE_POSITIVE = 1
    FALSE_NEGATIE = 2
    TRUE_NEGATIE = 3


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
