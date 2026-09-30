"""add the RescoreComparisons task type

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-30 14:00:00.000000

The comparator's scale changed from a 0-1 similarity to a 0-15 match score,
and both are valid readings of a stored number. Nothing can be converted in
SQL — the per-field scores went through a curve that is not invertible — so
the move is a task that recomputes every score from the MARC, and this is the
task type it runs under.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: str | Sequence[str] | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLAlchemy persists StrEnum member names, rather than their string values.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'RescoreComparisons'")


def downgrade() -> None:
    # PostgreSQL does not support removing individual enum labels.
    pass
