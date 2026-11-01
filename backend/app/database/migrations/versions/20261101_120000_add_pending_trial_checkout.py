"""Remember which Checkout session claimed the one trial.

Revision ID: d9f3b2c8e1a7
Revises: c8e2a1b7d4f6
"""

from alembic import op
import sqlalchemy as sa

revision = "d9f3b2c8e1a7"
down_revision = "c8e2a1b7d4f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("pending_trial_checkout_id", sa.String(255), nullable=True),
    )


def downgrade():
    op.drop_column("users", "pending_trial_checkout_id")
