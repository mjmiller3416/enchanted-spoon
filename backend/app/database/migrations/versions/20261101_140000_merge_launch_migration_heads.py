"""merge launch migration heads

Revision ID: b8e4c1a7d2f9
Revises: a7c2e9b4d1f0, f6b2c8d4e1a7, e7b1c4a9d2f6
Create Date: 2026-11-01 02:45:00

Joins the soft-launch billing chain, household sharing, and native
push/store migrations so `alembic upgrade head` has one target after
the release PRs land together.
"""
from typing import Sequence, Union

revision: str = "b8e4c1a7d2f9"
down_revision: Union[str, Sequence[str], None] = (
    "a7c2e9b4d1f0",
    "f6b2c8d4e1a7",
    "e7b1c4a9d2f6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
