"""Record why a catalog record could not be processed

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: str | Sequence[str] | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable and left unset. A record that is broken today is broken for a
    # reason only a processing pass can state, and it will state it the next
    # time it reaches the record — which it does, because a record that never
    # got stamped is retried on every run. Backfilling would mean guessing.
    op.add_column(
        "catalog_records",
        sa.Column("processing_error", sa.String(), nullable=True),
    )
    # The whole point is finding them, and they are a tiny minority of the
    # table, so the index only carries the rows that have one.
    op.create_index(
        "idx_catalog_records_processing_error",
        "catalog_records",
        ["processing_error"],
        postgresql_where=sa.text("processing_error IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_catalog_records_processing_error", table_name="catalog_records")
    op.drop_column("catalog_records", "processing_error")
