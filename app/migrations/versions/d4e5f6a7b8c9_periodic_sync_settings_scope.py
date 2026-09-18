"""add periodic-sync value to settingsscope enum

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-07 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The enum labels are the SettingsScope *member names* ('Catalog', 'Tasks', …),
    # not their values — that is what SQLAlchemy's Enum() persists and queries by.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE settingsscope ADD VALUE IF NOT EXISTS 'PeriodicSync'")


def downgrade() -> None:
    # Postgres cannot drop a single enum value; 'PeriodicSync' is left in place.
    pass
