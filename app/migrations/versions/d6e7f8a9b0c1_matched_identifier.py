"""record which identifier retrieved a link, not only that one did

Revision ID: d6e7f8a9b0c1
Revises: b4c5d6e7f8a9
Create Date: 2026-09-30 19:30:00.000000

`matched_by` says a pair was found by identifier. It does not say which, and
the kinds are not equally good evidence: a shared national bibliography number
makes a low-scoring pair a finding worth acting on, a shared ISSN makes the
same score mean two issues of one serial. Nullable and not backfilled here —
the value is known only to the linker that retrieved the pair, so it fills in
on the next pass, which the update guard now allows for.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: str | Sequence[str] | None = "b4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("authority_links", sa.Column("matched_identifier", sa.String(), nullable=True))
    op.create_index(
        "ix_authority_links_matched_identifier", "authority_links", ["matched_identifier"]
    )


def downgrade() -> None:
    op.drop_index("ix_authority_links_matched_identifier", table_name="authority_links")
    op.drop_column("authority_links", "matched_identifier")
