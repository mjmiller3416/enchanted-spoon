"""Scheduled trial reminder pushes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TrialNudge(Base):
    """One reminder per account per kind. ``sent_at`` stays empty until delivery."""

    __tablename__ = "trial_nudges"
    __table_args__ = (UniqueConstraint("user_id", "kind", name="uq_trial_nudges_user_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
