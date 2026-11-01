"""merge billing and household migration heads

Revision ID: c4a8e2b1d7f3
Revises: e7b1c4a9d2f6, f6b2c8d4e1a7
Create Date: 2026-11-01 02:50:00

#208 includes the soft-launch billing chain and household tables, which
both revise e4a9c2d7b1f3. This empty revision gives that branch one head.
#209 joins this revision with the native push migration.
"""
from typing import Sequence, Union

revision: str = "c4a8e2b1d7f3"
down_revision: Union[str, Sequence[str], None] = ("e7b1c4a9d2f6", "f6b2c8d4e1a7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
