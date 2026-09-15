"""app/models/user_settings.py

SQLAlchemy ORM model for user preferences/settings.
Stores settings as JSON for flexibility.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


# Default settings for new users
from app.dtos.settings_dtos import SettingsDTO

DEFAULT_SETTINGS: Dict[str, Any] = SettingsDTO().model_dump()


class UserSettings(Base):
    """
    User preferences and application settings.

    Settings are stored as JSON for flexibility - new settings can be
    added without migrations. The frontend useSettings hook syncs with this.
    """
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    _settings_json: Mapped[str] = mapped_column(
        "settings_json",
        Text,
        default=lambda: json.dumps(DEFAULT_SETTINGS),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False
    )

    # ── Relationship ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", backref="settings", uselist=False)

    # ── Properties ──────────────────────────────────────────────────────────
    @property
    def settings(self) -> Dict[str, Any]:
        """Get settings as dictionary."""
        try:
            return json.loads(self._settings_json)
        except (json.JSONDecodeError, TypeError):
            return DEFAULT_SETTINGS.copy()

    @settings.setter
    def settings(self, value: Dict[str, Any]) -> None:
        """Set settings from dictionary."""
        # Merge with defaults to ensure all keys exist
        merged = DEFAULT_SETTINGS.copy()
        merged.update(value)
        self._settings_json = json.dumps(merged)

    # ── Helper Methods ──────────────────────────────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a specific setting value."""
        current = self.settings
        current[key] = value
        self.settings = current

    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id})>"
