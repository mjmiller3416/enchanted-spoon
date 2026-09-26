"""Add user_id to ingredients and unit_conversion_rules

Revision ID: h8i9j0k1l2m3
Revises: efdfb2d763f7
Create Date: 2026-01-26 18:00:00.000000

Adds user ownership to ingredients and unit conversion rules tables.
Existing data is assigned to user_id=1 (Maryann).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine import reflection


# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, Sequence[str], None] = 'efdfb2d763f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_unique_constraint_name(table_name: str, columns: list[str]) -> str | None:
    """Find the name of a unique constraint on the given columns."""
    bind = op.get_bind()
    inspector = inspect(bind)

    for constraint in inspector.get_unique_constraints(table_name):
        if set(constraint['column_names']) == set(columns):
            return constraint['name']
    return None


def constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists on the table."""
    bind = op.get_bind()
    inspector = inspect(bind)

    for constraint in inspector.get_unique_constraints(table_name):
        if constraint['name'] == constraint_name:
            return True
    return False


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def foreign_key_exists(table_name: str, fk_name: str) -> bool:
    """Check if a foreign key exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    fks = [fk['name'] for fk in inspector.get_foreign_keys(table_name)]
    return fk_name in fks


def upgrade() -> None:
    """Upgrade schema.

    Adds user_id column to ingredients and unit_conversion_rules tables
    for multi-user support. Existing data is assigned to user_id=1 (Maryann).
    """
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    # --- Ingredients ---
    if is_sqlite:
        # A fresh database may already have the column from an earlier revision
        if not column_exists('ingredients', 'user_id'):
            # For SQLite, we need batch mode to handle constraint changes
            with op.batch_alter_table('ingredients', recreate='always') as batch_op:
                # Add user_id column (with default for existing rows)
                batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))

                # Create index for fast user lookups
                batch_op.create_index('ix_ingredients_user_id', ['user_id'], unique=False)

                # Add foreign key to users table
                batch_op.create_foreign_key(
                    'fk_ingredients_user_id',
                    'users',
                    ['user_id'],
                    ['id'],
                    ondelete='CASCADE'
                )

                # Drop old unique constraint and create new one that includes user_id
                # Try known constraint names
                old_constraint = get_unique_constraint_name('ingredients', ['ingredient_name', 'ingredient_category'])
                if old_constraint:
                    batch_op.drop_constraint(old_constraint, type_='unique')

                batch_op.create_unique_constraint(
                    'uq_ingredient_user_name_category',
                    ['user_id', 'ingredient_name', 'ingredient_category']
                )

            # Remove the server default after migration (not needed for new rows)
            with op.batch_alter_table('ingredients') as batch_op:
                batch_op.alter_column('user_id', server_default=None)
    else:
        # PostgreSQL - use native ALTER TABLE operations
        # All operations are idempotent to handle partial migration state

        # Add user_id column with default (if not already added)
        if not column_exists('ingredients', 'user_id'):
            op.add_column('ingredients', sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))

        # Create index (if not already created)
        if not index_exists('ingredients', 'ix_ingredients_user_id'):
            op.create_index('ix_ingredients_user_id', 'ingredients', ['user_id'], unique=False)

        # Add foreign key (if not already added)
        if not foreign_key_exists('ingredients', 'fk_ingredients_user_id'):
            op.create_foreign_key(
                'fk_ingredients_user_id',
                'ingredients',
                'users',
                ['user_id'],
                ['id'],
                ondelete='CASCADE'
            )

        # Drop old unique constraint if it exists (find actual name)
        old_constraint = get_unique_constraint_name('ingredients', ['ingredient_name', 'ingredient_category'])
        if old_constraint:
            op.drop_constraint(old_constraint, 'ingredients', type_='unique')

        # Create new unique constraint with user_id (if not already created)
        if not constraint_exists('ingredients', 'uq_ingredient_user_name_category'):
            op.create_unique_constraint(
                'uq_ingredient_user_name_category',
                'ingredients',
                ['user_id', 'ingredient_name', 'ingredient_category']
            )

        # Remove server default (safe to run multiple times)
        op.alter_column('ingredients', 'user_id', server_default=None)

    # --- Unit Conversion Rules ---
    if is_sqlite:
        # A fresh database may already have the column from an earlier revision
        if not column_exists('unit_conversion_rules', 'user_id'):
            with op.batch_alter_table('unit_conversion_rules', recreate='always') as batch_op:
                # Add user_id column (with default for existing rows)
                batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))

                # Create index for fast user lookups
                batch_op.create_index('ix_unit_conversion_rules_user_id', ['user_id'], unique=False)

                # Add foreign key to users table
                batch_op.create_foreign_key(
                    'fk_unit_conversion_rules_user_id',
                    'users',
                    ['user_id'],
                    ['id'],
                    ondelete='CASCADE'
                )

            # Remove the server default after migration
            with op.batch_alter_table('unit_conversion_rules') as batch_op:
                batch_op.alter_column('user_id', server_default=None)
    else:
        # PostgreSQL - use native ALTER TABLE operations
        # All operations are idempotent to handle partial migration state

        # Add user_id column (if not already added)
        if not column_exists('unit_conversion_rules', 'user_id'):
            op.add_column('unit_conversion_rules', sa.Column('user_id', sa.Integer(), nullable=False, server_default='1'))

        # Create index (if not already created)
        if not index_exists('unit_conversion_rules', 'ix_unit_conversion_rules_user_id'):
            op.create_index('ix_unit_conversion_rules_user_id', 'unit_conversion_rules', ['user_id'], unique=False)

        # Add foreign key (if not already added)
        if not foreign_key_exists('unit_conversion_rules', 'fk_unit_conversion_rules_user_id'):
            op.create_foreign_key(
                'fk_unit_conversion_rules_user_id',
                'unit_conversion_rules',
                'users',
                ['user_id'],
                ['id'],
                ondelete='CASCADE'
            )

        # Remove server default (safe to run multiple times)
        op.alter_column('unit_conversion_rules', 'user_id', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    # --- Unit Conversion Rules ---
    if is_sqlite:
        with op.batch_alter_table('unit_conversion_rules', recreate='always') as batch_op:
            batch_op.drop_constraint('fk_unit_conversion_rules_user_id', type_='foreignkey')
            batch_op.drop_index('ix_unit_conversion_rules_user_id')
            batch_op.drop_column('user_id')
    else:
        op.drop_constraint('fk_unit_conversion_rules_user_id', 'unit_conversion_rules', type_='foreignkey')
        op.drop_index('ix_unit_conversion_rules_user_id', table_name='unit_conversion_rules')
        op.drop_column('unit_conversion_rules', 'user_id')

    # --- Ingredients ---
    if is_sqlite:
        with op.batch_alter_table('ingredients', recreate='always') as batch_op:
            # Drop new unique constraint and recreate old one
            batch_op.drop_constraint('uq_ingredient_user_name_category', type_='unique')
            batch_op.create_unique_constraint(
                'uq_ingredient_name_category',
                ['ingredient_name', 'ingredient_category']
            )
            batch_op.drop_constraint('fk_ingredients_user_id', type_='foreignkey')
            batch_op.drop_index('ix_ingredients_user_id')
            batch_op.drop_column('user_id')
    else:
        op.drop_constraint('uq_ingredient_user_name_category', 'ingredients', type_='unique')
        op.create_unique_constraint(
            'uq_ingredient_name_category',
            'ingredients',
            ['ingredient_name', 'ingredient_category']
        )
        op.drop_constraint('fk_ingredients_user_id', 'ingredients', type_='foreignkey')
        op.drop_index('ix_ingredients_user_id', table_name='ingredients')
        op.drop_column('ingredients', 'user_id')
