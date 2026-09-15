"""app/core/dtos/planner_dtos.py

Pydantic DTOs for planner entry operations.
Handles only planner state - meal DTOs are in meal_dtos.py.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

from datetime import date
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field

from .recipe_dtos import RecipeCardDTO


# -- Planner Entry DTOs --------------------------------------------------------------------------
class PlannerEntryCreateDTO(BaseModel):
    """DTO for adding a meal to the planner."""

    model_config = ConfigDict(from_attributes=True)

    meal_id: int = Field(..., ge=1, description="ID of the meal to add")
    position: Optional[int] = Field(None, ge=0, description="Position in the planner (optional)")


class PlannerShoppingModeDTO(BaseModel):
    """Explicit desired shopping state; safe to repeat after a lost response."""

    shopping_mode: Literal["all", "produce_only", "none"]


class PlannerEntryUpdateDTO(BaseModel):
    """DTO for updating a planner entry."""

    model_config = ConfigDict(from_attributes=True)

    position: Optional[int] = Field(None, ge=0)
    is_completed: Optional[bool] = None
    scheduled_date: Optional[date] = None
    shopping_mode: Optional[str] = Field(None, description="Shopping mode: 'all', 'produce_only', or 'none'")


class PlannerEntryResponseDTO(BaseModel):
    """DTO for planner entry responses with meal information."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    meal_id: int
    position: int
    is_completed: bool
    completed_at: Optional[str] = None  # ISO format datetime string
    scheduled_date: Optional[str] = None  # ISO format date string
    shopping_mode: str = "all"  # 'all', 'produce_only', or 'none'

    # Meal information (denormalized for convenience)
    meal_name: Optional[str] = None
    meal_is_saved: Optional[bool] = None
    main_recipe_id: Optional[int] = None
    side_recipe_ids: List[int] = Field(default_factory=list)
    main_recipe: Optional[RecipeCardDTO] = None


# -- Planner Summary DTO -------------------------------------------------------------------------
class PlannerSummaryDTO(BaseModel):
    """DTO for planner summary information."""

    model_config = ConfigDict(from_attributes=True)

    total_entries: int
    completed_entries: int
    incomplete_entries: int
    total_recipes: int
    meal_names: List[str]
    is_at_capacity: bool
    max_capacity: int = 15
    error: Optional[str] = None


# -- Reorder DTO ---------------------------------------------------------------------------------
class PlannerReorderDTO(BaseModel):
    """DTO for reordering planner entries."""

    model_config = ConfigDict(from_attributes=True)

    entry_ids: List[int] = Field(..., description="Entry IDs in desired order")


# -- Bulk Add DTO --------------------------------------------------------------------------------
class PlannerBulkAddDTO(BaseModel):
    """DTO for adding multiple meals to the planner."""

    model_config = ConfigDict(from_attributes=True)

    meal_ids: List[int] = Field(..., description="List of meal IDs to add")


# -- Operation Result DTO ------------------------------------------------------------------------
class PlannerOperationResultDTO(BaseModel):
    """DTO for planner operation results."""

    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str
    affected_count: int = 0
    error: Optional[str] = None


# -- Cooking Streak DTO --------------------------------------------------------------------------
class CookingStreakDTO(BaseModel):
    """DTO for cooking streak information."""

    model_config = ConfigDict(from_attributes=True)

    current_streak: int = Field(..., ge=0, description="Current consecutive day streak")
    longest_streak: int = Field(..., ge=0, description="Longest streak ever achieved")
    week_activity: List[bool] = Field(
        ..., description="Activity for current week [Mon, Tue, Wed, Thu, Fri, Sat, Sun]"
    )
    last_cooked_date: Optional[str] = Field(
        None, description="ISO format date of last cooked meal"
    )
    today_index: int = Field(
        ..., ge=0, le=6, description="Today's day index (0=Monday, 6=Sunday)"
    )


# Re-export RecipeCardDTO for convenience
__all__ = [
    "PlannerEntryCreateDTO",
    "PlannerEntryUpdateDTO",
    "PlannerEntryResponseDTO",
    "PlannerSummaryDTO",
    "PlannerReorderDTO",
    "PlannerBulkAddDTO",
    "PlannerOperationResultDTO",
    "CookingStreakDTO",
    "RecipeCardDTO",
]
