"""add_last_active_at_to_users

Records each user's most recent authenticated request so the admin panel can
show who is actually using the app, not just who signed up.

Revision ID: d8b3f5a1c6e2
Revises: c7e1f4a92b30
Create Date: 2026-09-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8b3f5a1c6e2'
down_revision: Union[str, Sequence[str], None] = 'c7e1f4a92b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('last_active_at')
