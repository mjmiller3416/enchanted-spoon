"""add_cancel_at_period_end_to_users

Revision ID: a4c9e2b71d05
Revises: 687a6a7ea1b6
Create Date: 2026-09-02 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a4c9e2b71d05'
down_revision: Union[str, Sequence[str], None] = '687a6a7ea1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('cancel_at_period_end', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'cancel_at_period_end')
