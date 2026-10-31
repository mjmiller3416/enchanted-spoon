"""Add minimal, transactional billing event receipts and review queue.

Revision ID: a6c1e4f9d3b5
Revises: f5b0d3e8c2a4
"""
from alembic import op
import sqlalchemy as sa

revision = "a6c1e4f9d3b5"
down_revision = "f5b0d3e8c2a4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("billing_events",
        sa.Column("event_id", sa.String(255), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("outcome", sa.String(50), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("billing_events")
