"""add alexa_links for Alexa voice pairing

Revision ID: f2a8c4e6b1d7
Revises: e1f4a7c2b9d3
Create Date: 2026-11-15 19:00:00

An Alexa account (its skill userId, as a SHA-256 digest), a pending spoken
pairing code (digest) and the Enchanted Spoon account it's linked to
(app/models/alexa_link.py).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a8c4e6b1d7"
down_revision: Union[str, Sequence[str], None] = "e1f4a7c2b9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create alexa_links."""
    op.create_table(
        "alexa_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("alexa_user_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("code_hash", sa.String(length=64), nullable=True),
        sa.Column("code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alexa_links_alexa_user_hash", "alexa_links", ["alexa_user_hash"], unique=True)
    op.create_index("ix_alexa_links_user_id", "alexa_links", ["user_id"])
    op.create_index("ix_alexa_links_code_hash", "alexa_links", ["code_hash"])


def downgrade() -> None:
    """Drop alexa_links."""
    op.drop_index("ix_alexa_links_code_hash", table_name="alexa_links")
    op.drop_index("ix_alexa_links_user_id", table_name="alexa_links")
    op.drop_index("ix_alexa_links_alexa_user_hash", table_name="alexa_links")
    op.drop_table("alexa_links")
