"""tasks.attempts + tasks.heartbeat (redelivery poison guard + reaper)

Revision ID: b7e1c2a3d4f5
Revises: 7c1f3a9d42be
Create Date: 2026-07-07 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7e1c2a3d4f5'
down_revision: str | Sequence[str] | None = '7c1f3a9d42be'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # attempts: bounds redeliveries under acks_late (poison-message guard).
    op.add_column(
        'tasks',
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    # heartbeat: liveness timestamp for the orphaned-task reaper.
    op.add_column(
        'tasks',
        sa.Column('heartbeat', sa.TIMESTAMP(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('tasks', 'heartbeat')
    op.drop_column('tasks', 'attempts')
