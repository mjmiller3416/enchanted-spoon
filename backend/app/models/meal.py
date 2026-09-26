"""app/core/models/meal.py

SQLAlchemy ORM model for meals (saved meal configurations).
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.base import Base

if TYPE_CHECKING:
    from .planner_entry import PlannerEntry
    from .recipe import Recipe
    from .user import User


def _utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


# -- Meal Model ----------------------------------------------------------------------------------
class Meal(Base):
    """
    Represents a saved meal configuration with one main recipe and optional side recipes.

    A meal is a reusable entity that can be added to the planner multiple times.
    Meals persist independently of planner state.
    """
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meal_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # User ID - defaults to 1 for single-user/auth-disabled testing
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Main recipe (required) - CASCADE delete when recipe is deleted
    main_recipe_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recipe.id", ondelete="CASCADE"),
        nullable=False
    )

    # Side recipe IDs stored as JSON array (0-3 items, ordered)
    # Using Text to store JSON string for SQLite compatibility
    _side_recipe_ids_json: Mapped[Optional[str]] = mapped_column(
        "side_recipe_ids",
        Text,
        nullable=True,
        default="[]"
    )

    # Saved flag - transient meals are deleted when they leave the planner
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)

    # Starter-pack meal seeded for a new account; cleared once the user edits it
    is_sample: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False, index=True
    )

    # Tags stored as JSON array of strings
    _tags_json: Mapped[Optional[str]] = mapped_column(
        "tags",
        Text,
        nullable=True,
        default="[]"
    )

    # Timestamp for creation
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow
    )

    # User ownership
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # -- Relationships ---------------------------------------------------------------------------
    main_recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        foreign_keys=[main_recipe_id],
        back_populates="main_meals"
    )

    planner_entries: Mapped[List["PlannerEntry"]] = relationship(
        "PlannerEntry",
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    user: Mapped["User"] = relationship("User", back_populates="meals")

    # -- Properties for JSON fields --------------------------------------------------------------
    @property
    def side_recipe_ids(self) -> List[int]:
        """Get the list of side recipe IDs."""
        import json
        if not self._side_recipe_ids_json:
            return []
        try:
            return json.loads(self._side_recipe_ids_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @side_recipe_ids.setter
    def side_recipe_ids(self, value: List[int]) -> None:
        """Set the list of side recipe IDs (max 3)."""
        import json
        if value is None:
            value = []
        if len(value) > 3:
            raise ValueError("Maximum of 3 side recipes allowed")
        self._side_recipe_ids_json = json.dumps(value)

    @property
    def tags(self) -> List[str]:
        """Get the list of tags."""
        import json
        if not self._tags_json:
            return []
        try:
            return json.loads(self._tags_json)
        except (json.JSONDecodeError, TypeError):
            return []

    # Constants for tag validation
    MAX_TAGS = 20
    MAX_TAG_LENGTH = 50

    @tags.setter
    def tags(self, value: List[str]) -> None:
        """
        Set the list of tags with validation and normalization.

        Tags are normalized to lowercase and stripped of whitespace.
        Duplicates are removed while preserving order.

        Args:
            value: List of tag strings

        Raises:
            ValueError: If value is not a list, contains non-strings,
                       exceeds 20 tags, or any tag exceeds 50 characters
        """
        import json

        # Handle None case
        if value is None:
            self._tags_json = "[]"
            return

        # Type validation - must be a list
        if not isinstance(value, list):
            raise ValueError(f"Tags must be a list, got {type(value)}")

        # Type validation - all items must be strings
        if not all(isinstance(tag, str) for tag in value):
            raise ValueError("All tags must be strings")

        # Normalize tags: strip, lowercase, remove empty, deduplicate (preserve order)
        normalized: List[str] = []
        seen: set = set()
        for tag in value:
            tag_clean = tag.strip().lower()
            if tag_clean and tag_clean not in seen:
                seen.add(tag_clean)
                normalized.append(tag_clean)

        # Validate tag count
        if len(normalized) > self.MAX_TAGS:
            raise ValueError(f"Maximum {self.MAX_TAGS} tags allowed, got {len(normalized)}")

        # Validate individual tag length
        for tag in normalized:
            if len(tag) > self.MAX_TAG_LENGTH:
                display_tag = tag[:20] + "..." if len(tag) > 23 else tag
                raise ValueError(
                    f"Tag '{display_tag}' exceeds {self.MAX_TAG_LENGTH} character limit"
                )

        self._tags_json = json.dumps(normalized)

    # -- String Representation -------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<Meal(id={self.id}, meal_name='{self.meal_name}', "
            f"main_recipe_id={self.main_recipe_id}, "
            f"side_recipe_ids={self.side_recipe_ids})>"
        )

    # -- Helper Methods --------------------------------------------------------------------------
    def add_side_recipe(self, recipe_id: int) -> bool:
        """
        Add a side recipe ID if space is available.

        Args:
            recipe_id: The recipe ID to add

        Returns:
            True if added, False if already at max capacity or already exists
        """
        current = self.side_recipe_ids
        if len(current) >= 3:
            return False
        if recipe_id in current:
            return False
        current.append(recipe_id)
        self.side_recipe_ids = current
        return True

    def remove_side_recipe(self, recipe_id: int) -> bool:
        """
        Remove a side recipe ID from the list.

        Args:
            recipe_id: The recipe ID to remove

        Returns:
            True if removed, False if not found
        """
        current = self.side_recipe_ids
        if recipe_id not in current:
            return False
        current.remove(recipe_id)
        self.side_recipe_ids = current
        return True

    def get_all_recipe_ids(self) -> List[int]:
        """Return all recipe IDs (main + sides) for this meal."""
        return [self.main_recipe_id] + self.side_recipe_ids

    def has_recipe(self, recipe_id: int) -> bool:
        """Check if this meal contains a specific recipe (main or side)."""
        return recipe_id == self.main_recipe_id or recipe_id in self.side_recipe_ids
