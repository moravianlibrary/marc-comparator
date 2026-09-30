"""a cataloguer's verdict on a pair of records

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-30 17:30:00.000000

Keyed by the candidate's natural key and not by a catalogue row, because a
candidate nobody accepted has no row in our catalogue and a claim has to be
able to name one — overruling the machine's answer in favour of a runner-up is
the point of the table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c5d6e7f8a9"
down_revision: str | Sequence[str] | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "link_claims",
        sa.Column("main_record_id", sa.String(), nullable=False),
        sa.Column("base", sa.String(), nullable=False),
        sa.Column("authority_base", sa.String(), nullable=False),
        sa.Column("authority_sysno", sa.String(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("claimed_by", sa.UUID(), nullable=False),
        sa.Column("claimed_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("claimed_confidence", sa.Float(), nullable=True),
        sa.Column("rival_confidence", sa.Float(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["main_record_id"], ["catalog_records.id"]),
        sa.ForeignKeyConstraint(["claimed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("main_record_id", "base", "authority_base", "authority_sysno"),
    )
    op.create_index("ix_link_claims_lookup", "link_claims", ["main_record_id", "base"])
    op.create_index("ix_link_claims_needs_review", "link_claims", ["needs_review"])


def downgrade() -> None:
    op.drop_index("ix_link_claims_needs_review", table_name="link_claims")
    op.drop_index("ix_link_claims_lookup", table_name="link_claims")
    op.drop_table("link_claims")
