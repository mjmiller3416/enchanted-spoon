"""app/core/models/recipe.py

SQLAlchemy model for recipes.
"""

# ── Imports ─────────────────────────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, case, false, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)

from ..database.base import Base
from ..dtos.ingredient_dtos import IngredientDetailDTO
from .recipe_history import RecipeHistory
from .recipe_ingredient import RecipeIngredient

if TYPE_CHECKING:
    from .meal import Meal
    from .nutrition_facts import NutritionFacts
    from .recipe_group import RecipeGroup
    from .user import User


# ── Recipe Model ────────────────────────────────────────────────────────────────────────────────────────────
class Recipe(Base):
    __tablename__ = "recipe"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipe_name: Mapped[str] = mapped_column(String, nullable=False)
    recipe_category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String, default="Dinner", nullable=False, index=True)
    diet_pref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prep_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cook_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    servings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    directions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    banner_image_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Stable, environment-independent key for addressing this recipe's Cloudinary
    # image assets. Generated once at creation and preserved across backup/restore
    # and cross-database copies, so image URLs never collide with a different
    # recipe's auto-increment id in another environment (SQLite local vs Postgres prod).
    image_key: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False, default=lambda: uuid.uuid4().hex
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # Starter-pack recipe seeded for a new account; cleared once the user edits it
    is_sample: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False, index=True
    )
    # Original URL when the recipe was imported from a website (None otherwise)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # User ownership
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Relationships  ──────────────────────────────────────────────────────────────────────────────────────
    ingredients: Mapped[List[RecipeIngredient]] = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan"
    )

    history: Mapped[List[RecipeHistory]] = relationship(
        "RecipeHistory",
        back_populates="recipe",
        cascade="all, delete-orphan"
    )

    main_meals: Mapped[List["Meal"]] = relationship(
        "Meal",
        foreign_keys="Meal.main_recipe_id",
        back_populates="main_recipe",
        passive_deletes=True
    )

    user: Mapped["User"] = relationship("User", back_populates="recipes")

    groups: Mapped[List["RecipeGroup"]] = relationship(
        "RecipeGroup",
        secondary="recipe_group_association",
        back_populates="recipes"
    )

    nutrition_facts: Mapped[Optional["NutritionFacts"]] = relationship(
        "NutritionFacts",
        back_populates="recipe",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # ── Computed Properties ────────────────────────────────────────────────────────────────────────────────
    @hybrid_property
    def total_time(self) -> Optional[int]:
        if self.prep_time is None and self.cook_time is None:
            return None
        return (self.prep_time or 0) + (self.cook_time or 0)

    @total_time.inplace.expression
    @classmethod
    def _total_time_expr(cls):
        return case(
            (cls.prep_time.is_(None) & cls.cook_time.is_(None), None),
            else_=func.coalesce(cls.prep_time, 0) + func.coalesce(cls.cook_time, 0),
        )

    # ── String Representation ───────────────────────────────────────────────────────────────────────────────
    def __repr__(self) -> str:
        return (
            f"Recipe(id={self.id}, recipe_name={self.recipe_name}, "
            f"recipe_category={self.recipe_category}, meal_type={self.meal_type}, "
            f"total_time={self.total_time}, servings={self.servings}, "
            f"is_favorite={self.is_favorite})"
        )

    # ── Helper Methods ──────────────────────────────────────────────────────────────────────────────────────
    def formatted_time(self) -> str:
        """Return total_time formatted as "Xh Ym" or "Ym" if less than 1 hour."""
        if not self.total_time:
            return ""
        hrs, mins = divmod(self.total_time, 60)
        return f"{hrs}h {mins}m" if hrs else f"{mins}m"

    def formatted_servings(self) -> str:
        """Return servings with label."""
        return f"{self.servings}" if self.servings else ""

    def get_directions_list(self) -> list[str]:
        """Return each non-empty line as a step."""
        if not self.directions:
            return []
        return [line.strip() for line in self.directions.splitlines() if line.strip()]

    def get_ingredient_details(self) -> list[IngredientDetailDTO]:
        """Return list of IngredientDetailDTO for each ingredient."""
        return [ri.get_ingredient_detail() for ri in self.ingredients]
