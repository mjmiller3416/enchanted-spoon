"""add_is_sample_to_recipe_and_meals

Flags starter-pack content seeded for new accounts so it can be removed in
one step from Settings without touching the user's own recipes and meals.

Revision ID: c7e1f4a92b30
Revises: a4c9e2b71d05
Create Date: 2026-09-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c7e1f4a92b30'
down_revision: Union[str, Sequence[str], None] = 'a4c9e2b71d05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('recipe') as batch_op:
        batch_op.add_column(
            sa.Column('is_sample', sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.create_index('ix_recipe_is_sample', ['is_sample'])

    with op.batch_alter_table('meals') as batch_op:
        batch_op.add_column(
            sa.Column('is_sample', sa.Boolean(), server_default=sa.false(), nullable=False)
        )
        batch_op.create_index('ix_meals_is_sample', ['is_sample'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('meals') as batch_op:
        batch_op.drop_index('ix_meals_is_sample')
        batch_op.drop_column('is_sample')

    with op.batch_alter_table('recipe') as batch_op:
        batch_op.drop_index('ix_recipe_is_sample')
        batch_op.drop_column('is_sample')
