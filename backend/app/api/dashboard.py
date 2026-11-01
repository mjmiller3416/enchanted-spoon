"""API router for dashboard stats."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.dashboard_dtos import DashboardStatsDTO
from app.models.household import shared_recipe_id_select
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.models.shopping_item import ShoppingItem
from app.models.user import User
from app.services.household.scope import kitchen_user_id

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsDTO)
def get_dashboard_stats(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DashboardStatsDTO:
    """
    Get lightweight dashboard statistics using COUNT queries for the current user.

    Returns counts for total recipes, favorites, planned meals, and shopping items.
    Much faster than fetching full objects.
    """
    user_id = current_user.id
    kitchen_id = kitchen_user_id(session, current_user)
    visible_recipes = or_(
        Recipe.user_id == user_id,
        Recipe.id.in_(shared_recipe_id_select(user_id)),
    )

    # Own recipes plus the household cookbook
    total_recipes = (
        session.query(func.count(Recipe.id))
        .filter(visible_recipes)
        .scalar() or 0
    )

    # Count favorite recipes for user
    favorites = (
        session.query(func.count(Recipe.id))
        .filter(Recipe.user_id == user_id)
        .filter(Recipe.is_favorite == True)
        .scalar() or 0
    )

    # Household members share the owner's planner and shopping list
    meals_planned = (
        session.query(func.count(PlannerEntry.id))
        .filter(PlannerEntry.user_id == kitchen_id)
        .filter(PlannerEntry.is_cleared == False)
        .filter(PlannerEntry.is_completed == False)
        .scalar() or 0
    )

    shopping_items = (
        session.query(func.count(ShoppingItem.id))
        .filter(ShoppingItem.user_id == kitchen_id)
        .scalar() or 0
    )

    return DashboardStatsDTO(
        total_recipes=total_recipes,
        favorites=favorites,
        meals_planned=meals_planned,
        shopping_items=shopping_items,
    )
