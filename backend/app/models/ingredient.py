"""app/core/models/ingredient.py

SQLAlchemy model for the Ingredient table.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import backref, Mapped, mapped_column, relationship

from ..database.base import Base

if TYPE_CHECKING:
    from .recipe_ingredient import RecipeIngredient
    from .user import User


# ── Ingredient Model ────────────────────────────────────────────────────────────────────────────────────────
class Ingredient(Base):
    """SQLAlchemy model for Ingredient."""

    __tablename__ = "ingredients"

    # Add unique constraint for user + name + category combination (per-user uniqueness)
    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'ingredient_name',
            'ingredient_category',
            name='uq_ingredient_user_name_category'
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ingredient_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    ingredient_category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ── Relationships ───────────────────────────────────────────────────────────────────────────────────────
    recipe_links: Mapped[list[RecipeIngredient]] = relationship(
        "RecipeIngredient",
        back_populates="ingredient",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    # Cascade so deleting a user removes their ingredients instead of nulling a NOT NULL FK
    user: Mapped["User"] = relationship(
        "User", backref=backref("ingredients", cascade="all, delete-orphan")
    )

    # ── Helper Methods ──────────────────────────────────────────────────────────────────────────────────────
    def display_label(self) -> str:
        """Return a human-friendly label for this ingredient."""
        return f"{self.ingredient_name} ({self.ingredient_category})"
