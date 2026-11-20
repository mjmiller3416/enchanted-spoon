"""add feedback submissions

Durable copy of in-app feedback. An earlier ``feedback`` table was dropped
in 687a6a7ea1b6 when delivery moved to GitHub only. Submissions are stored
here again so a public or unconfigured tracker cannot drop them. Free text
is still never published unless the destination repository is private.

Revision ID: b3e7c1a9d4f6
Revises: f2a8c4e6b1d7
Create Date: 2026-11-20 00:07:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3e7c1a9d4f6"
down_revision: Union[str, Sequence[str], None] = "f2a8c4e6b1d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create feedback."""
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "delivery_status",
            sa.String(length=20),
            nullable=False,
            server_default="stored",
        ),
        sa.Column("issue_url", sa.String(length=512), nullable=True),
        sa.Column("error_reason", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    """Drop feedback."""
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
