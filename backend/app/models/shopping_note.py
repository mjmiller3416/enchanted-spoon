"""app/models/shopping_note.py

SQLAlchemy ORM model for the free-text notes pad on a user's shopping list.
One row per user, created lazily on first save.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import backref, Mapped, mapped_column, relationship

from ..database.base import Base


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class ShoppingNote(Base):
    """Free-text notes shown alongside the shopping list."""

    __tablename__ = "shopping_notes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    content: Mapped[str] = mapped_column(Text, default="", nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False
    )

    # ── Relationship ────────────────────────────────────────────────────────
    # Cascade so deleting a user removes their notes row (user_id is its primary key)
    user: Mapped["User"] = relationship(
        "User", backref=backref("shopping_note", uselist=False, cascade="all, delete-orphan")
    )

    def __repr__(self) -> str:
        return f"<ShoppingNote(user_id={self.user_id})>"
