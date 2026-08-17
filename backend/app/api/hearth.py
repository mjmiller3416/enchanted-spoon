"""app/api/hearth.py

Read-only meal endpoints for the Hearth wall-display integration.

Hearth is a trusted first-party household display. It authenticates with the
shared X-API-Key secret (``get_integration_user``) rather than a Clerk user
token, so every read here is scoped to the single ``INTEGRATION_USER_ID``
account — the same account the Tada shopping-list ingest writes to. This router
is READ-ONLY: it exposes the meal plan and meal cards the household already
sees in the Meal Planner; planning stays in the app (Hearth spec D6, §5.4).

Endpoints just project what the existing planner/meal/recipe services return
(see ``hearth_dtos`` mappers) — no new data-access logic, no writes.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import get_integration_user
from app.core.rate_limit import limiter
from app.database.db import get_session
from app.dtos.hearth_dtos import (
    HearthMealCardDTO,
    HearthMealPlanDTO,
    hearth_recipe_from_response,
    planned_meal_from_entry,
)
from app.dtos.recipe_dtos import RecipeResponseDTO
from app.models.user import User
from app.services.meal import MealService
from app.services.planner import PlannerService
from app.services.recipe_service import RecipeService

router = APIRouter()


@router.get("/meals", response_model=HearthMealPlanDTO)
@limiter.limit("60/minute")
def get_meal_plan(
    request: Request,
    session: Session = Depends(get_session),
    target_user: User = Depends(get_integration_user),
):
    """The current meal plan — the planner's entries in order.

    Enchanted Spoon's planner is a positional queue (max 15), so entries are
    returned in ``position`` order; each row carries a ``scheduled_date`` only
    when the household scheduled it. Read-only, scoped to the integration user.
    """
    entries = PlannerService(session, target_user.id).get_all_entries()
    return HearthMealPlanDTO(meals=[planned_meal_from_entry(e) for e in entries])


@router.get("/meals/{meal_id}", response_model=HearthMealCardDTO)
@limiter.limit("60/minute")
def get_meal_card(
    request: Request,
    meal_id: int,
    session: Session = Depends(get_session),
    target_user: User = Depends(get_integration_user),
):
    """One meal's card: the meal plus every recipe it's composed of (main dish
    first, then sides in order), each with ingredients and directions."""
    meal = MealService(session, target_user.id).get_meal(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    recipe_service = RecipeService(session, target_user.id)
    recipes = []

    main = recipe_service.get_recipe(meal.main_recipe_id)
    if main:
        recipes.append(
            hearth_recipe_from_response(RecipeResponseDTO.from_recipe(main), "main")
        )
    for side_id in meal.side_recipe_ids:
        side = recipe_service.get_recipe(side_id)
        if side:
            recipes.append(
                hearth_recipe_from_response(RecipeResponseDTO.from_recipe(side), "side")
            )

    return HearthMealCardDTO(
        meal_id=meal.id,
        meal_name=meal.meal_name,
        recipes=recipes,
    )
