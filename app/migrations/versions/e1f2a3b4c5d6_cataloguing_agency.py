"""Record who originally catalogued each record (040 $a).

A third of our accepted links point at a union-catalogue record MZK itself
catalogued — 14,230 of 47,777, and 12,624 of those score exactly 1.00, which
is 52% of the whole perfect-score population. For those the comparison is our
record against the copy we contributed, so there is no second opinion and
nothing to report to anybody. Without this column that population is
invisible and the review queue is 30% larger than it needs to be.

No backfill here: the value is read off the MARC, which lives in sector
storage rather than in SQL. Every record picks it up the next time it is
synced or linked, and the facet simply has fewer buckets until then.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catalog_records", sa.Column("cataloguing_agency", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("catalog_records", "cataloguing_agency")
