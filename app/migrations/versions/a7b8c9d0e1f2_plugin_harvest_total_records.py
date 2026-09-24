"""Record how many rows a plugin's local copy holds

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable and left unset: only the plugin can count its own rows, so the
    # figure appears after the next harvest rather than being guessed here.
    op.add_column(
        "plugin_harvest_state",
        sa.Column("total_records", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("plugin_harvest_state", "total_records")
