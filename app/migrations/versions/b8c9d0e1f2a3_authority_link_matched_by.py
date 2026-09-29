"""Record how a linker found the record it linked to

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable and left unset: which path found an existing link is not
    # recoverable from the row, and guessing it would put a claim in the column
    # that the next linking pass would silently overwrite. Links written before
    # this read as "not recorded" until they are next visited.
    op.add_column(
        "authority_links",
        sa.Column("matched_by", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("authority_links", "matched_by")
