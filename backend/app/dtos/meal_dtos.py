"""app/core/dtos/meal_dtos.py

Pydantic DTOs for meal operations.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from ..models.recipe import Recipe

from .recipe_dtos import RecipeCardDTO


# Mirrors Meal.MAX_TAGS / Meal.MAX_TAG_LENGTH (the model setter raises past these)
MAX_TAGS = 20
MAX_TAG_LENGTH = 50


def _validate_tags(v):
    """Normalize tags like the Meal model does, rejecting over-limit input with a 422."""
    if v is None:
        return v
    if not isinstance(v, list):
        raise ValueError("Tags must be a list")
    normalized: List[str] = []
    for tag in v:
        if not isinstance(tag, str):
            raise ValueError("Tags must be text")
        tag = tag.strip().lower()
        if not tag or tag in normalized:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise ValueError(f"Tags can be at most {MAX_TAG_LENGTH} characters")
        normalized.append(tag)
    if len(normalized) > MAX_TAGS:
        raise ValueError(f"A meal can have at most {MAX_TAGS} tags")
    return normalized


# -- Base DTO ------------------------------------------------------------------------------------
class MealBaseDTO(BaseModel):
    """Base DTO for meal operations."""

    model_config = ConfigDict(from_attributes=True)

    meal_name: str = Field(..., min_length=1, max_length=255)
    main_recipe_id: int = Field(..., ge=1)
    side_recipe_ids: List[int] = Field(default_factory=list, max_length=3)
    is_saved: bool = False
    tags: List[str] = Field(default_factory=list)

    @field_validator("meal_name", mode="before")
    @classmethod
    def strip_meal_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("side_recipe_ids", mode="before")
    @classmethod
    def validate_side_recipes(cls, v):
        if v is None:
            return []
        if len(v) > 3:
            raise ValueError("Maximum of 3 side recipes allowed")
        return v


# -- Create DTO ----------------------------------------------------------------------------------
class MealCreateDTO(MealBaseDTO):
    """DTO for creating a new meal."""

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        return _validate_tags(v) or []


# -- Update DTO ----------------------------------------------------------------------------------
class MealUpdateDTO(BaseModel):
    """DTO for updating an existing meal."""

    model_config = ConfigDict(from_attributes=True)

    meal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    main_recipe_id: Optional[int] = Field(None, ge=1)
    side_recipe_ids: Optional[List[int]] = Field(None, max_length=3)
    is_saved: Optional[bool] = None
    tags: Optional[List[str]] = None

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        return _validate_tags(v)

    @field_validator("meal_name", mode="before")
    @classmethod
    def strip_meal_name(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("side_recipe_ids", mode="before")
    @classmethod
    def validate_side_recipes(cls, v):
        if v is None:
            return None
        if len(v) > 3:
            raise ValueError("Maximum of 3 side recipes allowed")
        return v


# -- Response DTO --------------------------------------------------------------------------------
class MealResponseDTO(MealBaseDTO):
    """DTO for meal responses with full recipe information."""

    id: int
    created_at: Optional[str] = None  # ISO format datetime string
    main_recipe: Optional[RecipeCardDTO] = None
    side_recipes: List[RecipeCardDTO] = Field(default_factory=list)

    # Computed stats (calculated on the fly, not stored)
    total_cook_time: Optional[int] = None  # Sum of all recipe times in minutes
    avg_servings: Optional[int] = None     # Average servings rounded to nearest int
    times_cooked: Optional[int] = None     # Count of completed planner entries
    last_cooked: Optional[str] = None      # ISO datetime of most recent completion


# -- Filter DTO ----------------------------------------------------------------------------------
class MealFilterDTO(BaseModel):
    """DTO for filtering meals."""

    model_config = ConfigDict(from_attributes=True)

    name_pattern: Optional[str] = None
    tags: Optional[List[str]] = None
    saved_only: Optional[bool] = None
    limit: Optional[int] = Field(None, ge=1, le=100)
    offset: Optional[int] = Field(None, ge=0)


# -- Recipe Deletion Impact DTO ------------------------------------------------------------------
class RecipeDeletionImpactDTO(BaseModel):
    """DTO for showing the impact of deleting a recipe on meals."""

    model_config = ConfigDict(from_attributes=True)

    recipe_id: int
    meals_to_delete: List[MealResponseDTO] = Field(
        default_factory=list,
        description="Meals that will be deleted (recipe is their main)"
    )
    meals_to_update: List[MealResponseDTO] = Field(
        default_factory=list,
        description="Meals that will have this recipe removed from sides"
    )
    total_affected: int = 0

    @property
    def warning_message(self) -> str:
        """Generate user-friendly warning message for recipe deletion."""
        if not self.meals_to_delete and not self.meals_to_update:
            return ""

        def format_meal_list(meals: List[MealResponseDTO], max_display: int = 5) -> str:
            """Format a list of meals with truncation."""
            meal_names = [meal.meal_name for meal in meals]
            if len(meal_names) <= max_display:
                return ", ".join(meal_names)
            displayed = ", ".join(meal_names[:max_display])
            remaining = len(meal_names) - max_display
            return f"{displayed} and {remaining} more"

        def pluralize_meal(count: int) -> str:
            """Return 'meal' or 'meals' based on count."""
            return "meal" if count == 1 else "meals"

        parts = []

        if self.meals_to_delete:
            count = len(self.meals_to_delete)
            meal_list = format_meal_list(self.meals_to_delete)
            parts.append(
                f"⚠️ Deleting this recipe will DELETE {count} {pluralize_meal(count)}: {meal_list}"
            )

        if self.meals_to_update:
            count = len(self.meals_to_update)
            meal_list = format_meal_list(self.meals_to_update)
            if self.meals_to_delete:
                # Secondary message when there are also main meals
                parts.append(
                    f"It will also be removed as a side from {count} {pluralize_meal(count)}: {meal_list}"
                )
            else:
                # Primary message when only side meals affected
                parts.append(
                    f"⚠️ This recipe will be removed as a side from {count} {pluralize_meal(count)}: {meal_list}"
                )

        return "\n\n".join(parts)


# Re-export RecipeCardDTO for convenience
__all__ = [
    "MealBaseDTO",
    "MealCreateDTO",
    "MealUpdateDTO",
    "MealResponseDTO",
    "MealFilterDTO",
    "RecipeDeletionImpactDTO",
    "RecipeCardDTO",
]
