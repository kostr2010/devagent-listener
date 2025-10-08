import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import enum

SQL_BASE = sqlalchemy.ext.declarative.declarative_base()


class TaskKind(enum.IntEnum):
    TASK_KIND_CODE_REVIEW = 0  # Code review


class TaskStatus(enum.IntEnum):
    TASK_STATUS_IN_PROGRESS = 0  # Task is in progress
    TASK_STATUS_DONE = 1  # Task completed successfully
    TASK_STATUS_ERROR = 2  # Task completed abnormally
    TASK_STATUS_ABORTED = 3  # Task execution was aborted


class Task(SQL_BASE):
    __tablename__ = "tasks"

    # unique identifier for the task, used to query status
    task_id = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, nullable=False, unique=True
    )
    # kind of the task, used to start the routine
    task_kind = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    # status of the task, used to query status
    task_status = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    # additional payload, specific to each task_kind
    task_payload = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    # result after the task completion, specific to each task_status
    task_result = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    # timestamp of the task creation
    created_at = sqlalchemy.Column(
        sqlalchemy.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sqlalchemy.text("now()"),
    )
    # timestamp of the latest task update
    updated_at = sqlalchemy.Column(
        sqlalchemy.TIMESTAMP(timezone=True),
        nullable=False,
        server_default=sqlalchemy.text("now()"),
    )

    # validate that task is one of predetermined kinds
    @sqlalchemy.orm.validates("task_kind")
    def validate_task_kind(self, key, value):
        if not value in [e.value for e in TaskKind]:
            raise ValueError(f"Invalid task_kind value {value}")
        return value

    # validate that status is one of predetermined kinds
    @sqlalchemy.orm.validates("task_status")
    def validate_task_status(self, key, value):
        if not value in [e.value for e in TaskStatus]:
            raise ValueError(f"Invalid task_kind value {value}")
        return value
