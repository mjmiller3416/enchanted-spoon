"""Admin flag that keeps one account on the pre-release Pro allowances.

Revision ID: e7b1c4a9d2f6
Revises: d9f3b2c8e1a7
"""

from alembic import op
import sqlalchemy as sa

revision = "e7b1c4a9d2f6"
down_revision = "d9f3b2c8e1a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "usage_exempt",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column("users", "usage_exempt")
