"""add plugin-harvest settings scope and HarvestPlugin task type

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-18 20:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLAlchemy persists StrEnum member names, rather than their string values.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE settingsscope ADD VALUE IF NOT EXISTS 'PluginHarvest'")
        op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'HarvestPlugin'")


def downgrade() -> None:
    # PostgreSQL does not support removing individual enum labels.
    pass
