"""Add created_at and updated_at fields

Revision ID: ddcd9e8bf183
Revises: e5310dfaf8ae
Create Date: 2025-12-04 19:16:07.080551

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ddcd9e8bf183"
down_revision: Union[str, Sequence[str], None] = "e5310dfaf8ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "patches",
        sa.Column("created_at", sa.DateTime, default=sa.sql.func.now(), nullable=True),
    )
    op.add_column(
        "patches",
        sa.Column(
            "updated_at",
            sa.DateTime,
            default=sa.sql.func.now(),
            onupdate=sa.sql.func.now(),
            nullable=True,
        ),
    )
    op.add_column(
        "errors",
        sa.Column("created_at", sa.DateTime, default=sa.sql.func.now(), nullable=True),
    )
    op.add_column(
        "errors",
        sa.Column(
            "updated_at",
            sa.DateTime,
            default=sa.sql.func.now(),
            onupdate=sa.sql.func.now(),
            nullable=True,
        ),
    )
    op.add_column(
        "user_feedback",
        sa.Column("created_at", sa.DateTime, default=sa.sql.func.now(), nullable=True),
    )
    op.add_column(
        "user_feedback",
        sa.Column(
            "updated_at",
            sa.DateTime,
            default=sa.sql.func.now(),
            onupdate=sa.sql.func.now(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("patches", "created_at")
    op.drop_column("patches", "updated_at")
    op.drop_column("errors", "created_at")
    op.drop_column("errors", "updated_at")
    op.drop_column("user_feedback", "created_at")
    op.drop_column("user_feedback", "updated_at")
