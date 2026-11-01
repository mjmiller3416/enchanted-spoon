"""Trial window, read-only sunset, and reminder markers. No user backfill.

Revision ID: c8e2a1b7d4f6
Revises: a6c1e4f9d3b5
"""

from alembic import op
import sqlalchemy as sa

revision = "c8e2a1b7d4f6"
down_revision = "a6c1e4f9d3b5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("has_used_trial", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("read_only_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("sunset_notice_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("sunset_reminder_30_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("sunset_reminder_7_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("sunset_reminder_1_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("users", "sunset_reminder_1_sent_at")
    op.drop_column("users", "sunset_reminder_7_sent_at")
    op.drop_column("users", "sunset_reminder_30_sent_at")
    op.drop_column("users", "sunset_notice_seen_at")
    op.drop_column("users", "read_only_at")
    op.drop_column("users", "has_used_trial")
    op.drop_column("users", "trial_ends_at")
    op.drop_column("users", "trial_started_at")
