"""index validations.catalog_record_id

Revision ID: 7c1f3a9d42be
Revises: 523af0ba2cd5
Create Date: 2026-06-06 15:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7c1f3a9d42be'
down_revision: str | Sequence[str] | None = '523af0ba2cd5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # FK lookups (lazy/eager loads, analytics rebuild joins) seq-scan
    # validations without this index.
    op.create_index(
        'ix_validations_catalog_record_id',
        'validations',
        ['catalog_record_id'],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_validations_catalog_record_id',
        table_name='validations',
        if_exists=True,
    )
