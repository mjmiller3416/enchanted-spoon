"""app/models/alexa_link.py

Links an Alexa account (the skill's per-person ``userId``) to an Enchanted
Spoon account by a spoken pairing code, for households whose Alexa app won't
show the account-linking card.

The Alexa ``userId`` is stored only as a SHA-256 digest, and so is the code.
A row starts unlinked (``user_id`` empty, a code waiting); entering the code
in Settings fills ``user_id`` and clears the code.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class AlexaLink(Base):
    """One Alexa account, its pending pairing code, and the account it's linked to."""

    __tablename__ = "alexa_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alexa_user_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    code_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<AlexaLink(id={self.id}, user_id={self.user_id})>"
