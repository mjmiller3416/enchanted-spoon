"""app/dtos/hearth_dtos.py

DTOs for the Hearth wall-display integration (read-only meal surface).

Hearth is a household wall display that renders the current meal plan and, on
tap, a meal's card (ingredients + recipe). It authenticates as a trusted
first-party app via the shared X-API-Key secret (see ``get_integration_user``)
and reads the meal data of the single ``INTEGRATION_USER_ID`` account.

These shapes are a deliberately stable, self-contained integration CONTRACT:
Hearth's TypeScript client mirrors them 1:1. They are decoupled from the
internal planner/meal/recipe DTOs on purpose, so refactors of those internal
shapes don't silently break the wall. The mappers below are pure functions over
the existing internal DTOs, so no new data-access logic is introduced — the
endpoint just projects what the planner/meal/recipe services already return.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .planner_dtos import PlannerEntryResponseDTO
from .recipe_dtos import RecipeCardDTO, RecipeResponseDTO


# ── Card shapes ─────────────────────────────────────────────────────────────
class HearthIngredientDTO(BaseModel):
    """One ingredient line on a meal card. Quantity/unit may be absent (a
    recipe can list an ingredient without a measured amount)."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None


class HearthRecipeDTO(BaseModel):
    """One recipe within a meal card — the main dish or a side. Carries the
    detail the wall renders: ingredients and step-by-step directions, plus
    glanceable times and servings. ``steps`` is the recipe's ``directions``
    text split into lines so the wall can render an ordered list without doing
    its own parsing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: str  # "main" or "side"
    description: Optional[str] = None
    servings: Optional[int] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    total_time: Optional[int] = None
    difficulty: Optional[str] = None
    ingredients: List[HearthIngredientDTO] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    image_url: Optional[str] = None


class HearthMealCardDTO(BaseModel):
    """A meal's full card: its name and every recipe it's composed of (main
    first, then sides in order). This is what a Hearth tap opens (spec §4.5)."""

    model_config = ConfigDict(from_attributes=True)

    meal_id: int
    meal_name: str
    recipes: List[HearthRecipeDTO] = Field(default_factory=list)


# ── Plan shapes ─────────────────────────────────────────────────────────────
class HearthPlannedMealDTO(BaseModel):
    """One meal in the plan, as a glanceable row: name, its day when the entry
    is scheduled, and just enough about the main dish to preview it. Tapping a
    row fetches the card by ``meal_id``."""

    model_config = ConfigDict(from_attributes=True)

    entry_id: int
    meal_id: int
    meal_name: str
    position: int
    scheduled_date: Optional[str] = None  # ISO date; null = unscheduled queue entry
    is_completed: bool = False
    main_recipe_name: Optional[str] = None
    side_dish_count: int = 0
    total_time: Optional[int] = None  # of the main dish, minutes
    image_url: Optional[str] = None


class HearthMealPlanDTO(BaseModel):
    """The current meal plan: the planner's entries in order. Enchanted Spoon's
    planner is a positional queue (max 15) rather than a strict Mon–Sun grid,
    so Hearth renders the entries in ``position`` order and shows a day label
    only where ``scheduled_date`` is set."""

    model_config = ConfigDict(from_attributes=True)

    meals: List[HearthPlannedMealDTO] = Field(default_factory=list)


# ── Pure mappers (internal DTO → contract DTO) ──────────────────────────────
def _card_image(card: Optional[RecipeCardDTO]) -> Optional[str]:
    if card is None:
        return None
    return card.banner_image_path or card.reference_image_path


def planned_meal_from_entry(entry: PlannerEntryResponseDTO) -> HearthPlannedMealDTO:
    """Project a planner entry into a plan row."""
    main = entry.main_recipe
    return HearthPlannedMealDTO(
        entry_id=entry.id,
        meal_id=entry.meal_id,
        meal_name=entry.meal_name or (main.recipe_name if main else "Meal"),
        position=entry.position,
        scheduled_date=entry.scheduled_date,
        is_completed=entry.is_completed,
        main_recipe_name=main.recipe_name if main else None,
        side_dish_count=len(entry.side_recipe_ids),
        total_time=main.total_time if main else None,
        image_url=_card_image(main),
    )


def _steps_from_directions(directions: Optional[str]) -> List[str]:
    """Split a recipe's directions blob into renderable steps. Directions are
    stored as a single string, most often one step per line; splitting on
    newlines (dropping blanks) recovers the steps without guessing at prose
    that has none — a single-paragraph recipe simply yields one step."""
    if not directions:
        return []
    return [line.strip() for line in directions.splitlines() if line.strip()]


def hearth_recipe_from_response(recipe: RecipeResponseDTO, role: str) -> HearthRecipeDTO:
    """Project a full recipe response into a card recipe with the given role."""
    return HearthRecipeDTO(
        id=recipe.id,
        name=recipe.recipe_name,
        role=role,
        description=recipe.description,
        servings=recipe.servings,
        prep_time=recipe.prep_time,
        cook_time=recipe.cook_time,
        total_time=recipe.total_time,
        difficulty=recipe.difficulty,
        ingredients=[
            HearthIngredientDTO(
                name=ing.ingredient_name,
                quantity=ing.quantity,
                unit=ing.unit,
                category=ing.ingredient_category,
            )
            for ing in recipe.ingredients
        ],
        steps=_steps_from_directions(recipe.directions),
        notes=recipe.notes,
        image_url=recipe.banner_image_path or recipe.reference_image_path,
    )


__all__ = [
    "HearthIngredientDTO",
    "HearthRecipeDTO",
    "HearthMealCardDTO",
    "HearthPlannedMealDTO",
    "HearthMealPlanDTO",
    "planned_meal_from_entry",
    "hearth_recipe_from_response",
]
