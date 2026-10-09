"""index the record search's validation and listing filters

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-10-09 12:00:00.000000

The record search filters validations by `result->>'reason'` and
`result->>'status'` and lists records newest-synced first. None of the three
had an index, and the jsonb expressions had no statistics either: the planner
fell back to a default selectivity that put `no_links_found_or_expected` at
1/130th of the rows it matches, planned for that, and spent 1.6 s on a search
that takes 0.16 s with these in place (k3d, 345k records). An
expression index is also what gives Postgres statistics on its expression, so
the estimate is fixed by the same ANALYZE that follows.

`(source_type, latest_sync DESC)` serves the record list's newest-synced-first
order, which otherwise sorts every main record to return one page.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: str | Sequence[str] | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_validations_validator_reason",
        "validations",
        ["validator", sa.text("(result ->> 'reason')")],
        if_not_exists=True,
    )
    op.create_index(
        "ix_validations_validator_status",
        "validations",
        ["validator", sa.text("(result ->> 'status')")],
        if_not_exists=True,
    )
    op.create_index(
        "ix_catalog_records_source_type_latest_sync",
        "catalog_records",
        ["source_type", sa.text("latest_sync DESC")],
        if_not_exists=True,
    )
    # The new expression statistics only exist after the next ANALYZE, and
    # autovacuum may not get to a table this size for a while.
    op.execute("ANALYZE validations")
    op.execute("ANALYZE catalog_records")


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_records_source_type_latest_sync",
        table_name="catalog_records",
        if_exists=True,
    )
    op.drop_index(
        "ix_validations_validator_status",
        table_name="validations",
        if_exists=True,
    )
    op.drop_index(
        "ix_validations_validator_reason",
        table_name="validations",
        if_exists=True,
    )
