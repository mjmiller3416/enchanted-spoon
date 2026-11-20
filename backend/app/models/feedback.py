"""Stored user feedback.

The support tracker is optional. Every submission is saved here first so a
missing token, a public repository, or a GitHub outage cannot drop the text.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base

if TYPE_CHECKING:
    from .user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Feedback(Base):
    """One in-app feedback submission, kept even when no issue is filed."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    # "tracker" once a private issue exists; "stored" when only this row does.
    delivery_status: Mapped[str] = mapped_column(
        String(20), default="stored", server_default="stored", nullable=False
    )
    issue_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Short machine code (unset_config, not_private, http_error). Never the message.
    error_reason: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship(back_populates="feedback_submissions")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, user_id={self.user_id}, status={self.delivery_status})>"
