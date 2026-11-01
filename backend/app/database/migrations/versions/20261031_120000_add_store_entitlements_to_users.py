"""add store entitlement and trial columns to users

Keeps App Store / Play Billing state beside the Stripe columns so one
account can be Pro from either source without a second free trial.

Revision ID: f6a1c8e4b2d0
Revises: e4a9c2d7b1f3
Create Date: 2026-10-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a1c8e4b2d0"
down_revision: Union[str, Sequence[str], None] = "e4a9c2d7b1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("trial_consumed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("trial_provider", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("trial_transaction_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("store_provider", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("store_product_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("store_status", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("store_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "store_will_renew",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(sa.Column("store_original_transaction_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("store_environment", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("store_event_timestamp_ms", sa.BigInteger(), nullable=True))
        batch_op.create_index(
            "ix_users_store_original_transaction_id",
            ["store_original_transaction_id"],
            unique=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_store_original_transaction_id")
        batch_op.drop_column("store_event_timestamp_ms")
        batch_op.drop_column("store_environment")
        batch_op.drop_column("store_original_transaction_id")
        batch_op.drop_column("store_will_renew")
        batch_op.drop_column("store_expires_at")
        batch_op.drop_column("store_status")
        batch_op.drop_column("store_product_id")
        batch_op.drop_column("store_provider")
        batch_op.drop_column("trial_transaction_id")
        batch_op.drop_column("trial_provider")
        batch_op.drop_column("trial_consumed_at")
