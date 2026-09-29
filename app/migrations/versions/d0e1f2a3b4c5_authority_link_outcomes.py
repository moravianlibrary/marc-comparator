"""Let a record say why it has no authority link

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d0e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Every existing row is a link that was accepted, so the defaults describe
    # them exactly and the backfill below only has to fill in what was never
    # recorded. Server defaults are dropped at the end: they are here to get
    # the existing rows through the NOT NULL, not to let a future insert leave
    # an outcome unsaid.
    op.add_column(
        "authority_links",
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "authority_links",
        sa.Column("outcome", sa.String(), nullable=False, server_default="Linked"),
    )
    op.add_column("authority_links", sa.Column("authority_base", sa.String(), nullable=True))
    op.add_column("authority_links", sa.Column("authority_sysno", sa.String(), nullable=True))
    op.add_column("authority_links", sa.Column("candidate_count", sa.Integer(), nullable=True))
    op.add_column("authority_links", sa.Column("detail", sa.String(), nullable=True))

    # The candidate's natural key, taken from the record it points at rather
    # than by splitting the id on "-": `generate_id` joins base and system
    # number with one, and Aleph bases contain them (MZK01-UTF), so a split
    # would quietly cut those in the wrong place. The columns are one join away.
    op.execute(
        """
        UPDATE authority_links al
           SET authority_base = cr.base,
               authority_sysno = cr.system_number
          FROM catalog_records cr
         WHERE cr.id = al.authority_record_id
        """
    )

    # The key becomes (record, base, rank), so two links to one base would
    # collide at rank 0. Measured before writing this: no record holds links
    # from more than one linker. Asserted rather than assumed, because a
    # database where it is false must stop here and not lose a row to the
    # primary key it is about to gain.
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM ("
                "  SELECT 1 FROM authority_links"
                "   GROUP BY main_record_id, base HAVING count(*) > 1"
                ") d"
            )
        )
        .scalar()
    )
    if duplicates:
        raise RuntimeError(
            f"{duplicates} record/base pairs hold more than one authority link. "
            "Rank them by confidence before upgrading: the new primary key "
            "allows one row per rank, and this migration will not choose which "
            "link to keep on your behalf."
        )

    op.drop_constraint("authority_links_pkey", "authority_links", type_="primary")
    op.create_primary_key(
        "authority_links_pkey", "authority_links", ["main_record_id", "base", "rank"]
    )

    # Both become nullable together, and for the same reason: a row that says
    # why there is no link names no record and belongs to no linker.
    op.alter_column("authority_links", "authority_record_id", nullable=True)
    op.alter_column("authority_links", "linker", nullable=True)

    # One row per candidate per record and base, however many linkers propose
    # it. Partial, because the rows with no candidate are exactly the ones this
    # must not constrain — a record can only have one of those anyway, by the
    # primary key.
    op.create_index(
        "uq_authority_links_candidate",
        "authority_links",
        ["main_record_id", "base", "authority_base", "authority_sysno"],
        unique=True,
        postgresql_where=sa.text("authority_sysno IS NOT NULL"),
    )
    op.create_index("ix_authority_links_outcome", "authority_links", ["outcome"])

    op.alter_column("authority_links", "rank", server_default=None)
    op.alter_column("authority_links", "outcome", server_default=None)


def downgrade() -> None:
    # Only the accepted links fit the old shape. The rest say why a record has
    # no link, which the old table had no way to express, so they go.
    op.execute("DELETE FROM authority_links WHERE rank <> 0 OR outcome <> 'Linked'")

    op.drop_index("ix_authority_links_outcome", table_name="authority_links")
    op.drop_index("uq_authority_links_candidate", table_name="authority_links")

    op.alter_column("authority_links", "linker", nullable=False)
    op.alter_column("authority_links", "authority_record_id", nullable=False)

    op.drop_constraint("authority_links_pkey", "authority_links", type_="primary")
    op.create_primary_key(
        "authority_links_pkey", "authority_links", ["main_record_id", "linker", "base"]
    )

    op.drop_column("authority_links", "detail")
    op.drop_column("authority_links", "candidate_count")
    op.drop_column("authority_links", "authority_sysno")
    op.drop_column("authority_links", "authority_base")
    op.drop_column("authority_links", "outcome")
    op.drop_column("authority_links", "rank")
