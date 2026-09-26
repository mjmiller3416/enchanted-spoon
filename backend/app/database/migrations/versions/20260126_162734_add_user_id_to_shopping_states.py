"""add user_id to shopping_states

Revision ID: efdfb2d763f7
Revises: 4da72da66574
Create Date: 2026-01-26 16:27:34.725850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'efdfb2d763f7'
down_revision: Union[str, Sequence[str], None] = '4da72da66574'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Adds user_id column to shopping_states table for multi-user support.
    Existing shopping states are deleted since they cannot be attributed
    to a specific user and will be regenerated when users access their
    shopping lists.
    """
    # On a fresh database the shopping-refactor branch (h3c4d5e6f7g8) may run
    # first and drop shopping_states entirely; there is nothing to alter then
    if "shopping_states" not in sa.inspect(op.get_bind()).get_table_names():
        return

    # Delete existing shopping states - they will be regenerated per-user
    # This is safe because shopping states are transient data derived from planner
    op.execute("DELETE FROM shopping_states")

    # For SQLite, we need to use batch mode to handle constraint changes
    # This recreates the table with the new schema
    with op.batch_alter_table('shopping_states', recreate='always') as batch_op:
        # Add user_id column
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))

        # Create index for fast user lookups
        batch_op.create_index('ix_shopping_states_user_id', ['user_id'], unique=False)

        # Create composite unique constraint (user_id, key)
        batch_op.create_unique_constraint('uq_shopping_state_user_key', ['user_id', 'key'])

        # Add foreign key to users table
        batch_op.create_foreign_key(
            'fk_shopping_states_user_id',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Delete existing shopping states (multi-user data incompatible with single-user)
    op.execute("DELETE FROM shopping_states")

    # Use batch mode to handle constraint changes
    with op.batch_alter_table('shopping_states', recreate='always') as batch_op:
        # Drop foreign key
        batch_op.drop_constraint('fk_shopping_states_user_id', type_='foreignkey')

        # Drop unique constraint
        batch_op.drop_constraint('uq_shopping_state_user_key', type_='unique')

        # Drop index
        batch_op.drop_index('ix_shopping_states_user_id')

        # Drop column
        batch_op.drop_column('user_id')

        # Re-add old unique constraint on key only
        batch_op.create_unique_constraint(None, ['key'])
