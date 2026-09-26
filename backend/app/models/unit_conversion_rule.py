"""app/core/models/unit_conversion_rule.py

SQLAlchemy model for ingredient-specific unit conversion rules.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import backref, Mapped, mapped_column, relationship

from ..database.base import Base

if TYPE_CHECKING:
    from .user import User


# ── UnitConversionRule Model ───────────────────────────────────────────────────────────────────────────────
class UnitConversionRule(Base):
    """SQLAlchemy model for ingredient-specific unit conversion rules.

    Example: Convert butter from tablespoons to sticks (8 tbs = 1 stick).
    """

    __tablename__ = "unit_conversion_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ingredient_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    from_unit: Mapped[str] = mapped_column(String, nullable=False)
    to_unit: Mapped[str] = mapped_column(String, nullable=False)
    factor: Mapped[float] = mapped_column(Float, nullable=False)
    round_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ── Relationships ───────────────────────────────────────────────────────────────────────────────────────
    # Cascade so deleting a user removes their rules instead of nulling a NOT NULL FK
    user: Mapped["User"] = relationship(
        "User", backref=backref("unit_conversion_rules", cascade="all, delete-orphan")
    )
