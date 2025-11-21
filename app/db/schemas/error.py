import sqlalchemy
import sqlalchemy.ext.declarative


class Error(sqlalchemy.ext.declarative.declarative_base()):  # type: ignore
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
