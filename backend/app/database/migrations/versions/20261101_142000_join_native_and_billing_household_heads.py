"""join the native push head with the billing and household merge

Revision ID: d5b9f3c2e8a4
Revises: b8e4c1a7d2f9, c4a8e2b1d7f3
Create Date: 2026-11-01 02:52:00

#209 already merged the three launch heads in b8e4c1a7d2f9. #208 then
added c4a8e2b1d7f3 over billing and household only. This revision makes
one head again.
"""
from typing import Sequence, Union

revision: str = "d5b9f3c2e8a4"
down_revision: Union[str, Sequence[str], None] = ("b8e4c1a7d2f9", "c4a8e2b1d7f3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
