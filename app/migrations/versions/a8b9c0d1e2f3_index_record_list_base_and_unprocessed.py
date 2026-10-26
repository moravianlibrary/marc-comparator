"""index the record list by base and by unprocessed

Revision ID: a8b9c0d1e2f3
Revises: c4d5e6f7a8b9
Create Date: 2026-10-26 15:00:00.000000

The record list is ordered newest-synced first, and filtering it by base or
to unprocessed records only had `(source_type, latest_sync DESC)` to walk,
checking every row it passed. On 1.87M main records that took over two
minutes for MZK03, whose records all sort after MZK01's, and 17 s for the
633 unprocessed ones, each read row a random read on network storage. With
the filter in the key, or in a partial index's predicate, both read just the
page they return.

Built without CONCURRENTLY: migrations run at app startup, where waiting on
every open transaction could outlast the liveness probe and leave an invalid
index behind. Both builds take about 30 s at 3.4M catalog records, during
which writes to catalog_records wait and reads do not.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8b9c0d1e2f3"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_catalog_records_source_type_base_latest_sync",
        "catalog_records",
        ["source_type", "base", sa.text("latest_sync DESC")],
        if_not_exists=True,
    )
    op.create_index(
        "ix_catalog_records_unprocessed_latest_sync",
        "catalog_records",
        ["source_type", sa.text("latest_sync DESC")],
        postgresql_where=sa.text("processed_at IS NULL"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_records_unprocessed_latest_sync",
        table_name="catalog_records",
        if_exists=True,
    )
    op.drop_index(
        "ix_catalog_records_source_type_base_latest_sync",
        table_name="catalog_records",
        if_exists=True,
    )
