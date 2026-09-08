"""report_artifacts table + CreateReport task type

Revision ID: c3d4e5f6a7b8
Revises: b7e1c2a3d4f5
Create Date: 2026-07-07 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b7e1c2a3d4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # New enum value must be committed before it can be referenced.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'CreateReport'")

    op.create_table(
        "report_artifacts",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("tool", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False, server_default="application/zip"),
        sa.Column("blob", sa.LargeBinary(), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.task_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_report_artifacts_task_id",
        "report_artifacts",
        ["task_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_report_artifacts_task_id", table_name="report_artifacts", if_exists=True)
    op.drop_table("report_artifacts")
    # Note: Postgres cannot drop a single enum value; 'CreateReport' is left in
    # the tasktype enum on downgrade.
