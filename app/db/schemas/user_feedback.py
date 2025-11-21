import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import enum


class Feedback(enum.IntEnum):
    FALSE_POSITIVE = 0
    TRUE_POSITIVE = 1
    FALSE_NEGATIE = 2
    TRUE_NEGATIE = 3


class UserFeedback(sqlalchemy.ext.declarative.declarative_base()):  # type: ignore
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
    feedback: sqlalchemy.Column[Feedback] = sqlalchemy.Column(
        sqlalchemy.Enum(Feedback), nullable=False
    )
