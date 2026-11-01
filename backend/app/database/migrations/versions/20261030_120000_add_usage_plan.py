"""Preserve existing users' AI allowances when introducing launch limits.

Revision ID: f5b0d3e8c2a4
Revises: e4a9c2d7b1f3
"""
from alembic import op
import sqlalchemy as sa

revision = "f5b0d3e8c2a4"
down_revision = "e4a9c2d7b1f3"
branch_labels = None
depends_on = None


def upgrade():
    # The database default also preserves old application writers during rollout.
    # The new ORM explicitly supplies launch for genuinely new accounts.
    op.add_column("users", sa.Column("usage_plan", sa.String(20), nullable=False, server_default="legacy"))


def downgrade():
    op.drop_column("users", "usage_plan")
