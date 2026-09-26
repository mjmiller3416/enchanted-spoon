"""app/api/meals.py

FastAPI router for meal endpoints.
Handles meal CRUD operations (separate from planner state).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.meal_dtos import (
    MealCreateDTO,
    MealFilterDTO,
    MealResponseDTO,
    MealUpdateDTO,
)
from app.models.user import User
from app.services.meal import (
    InvalidRecipeError,
    MealSaveError,
    MealService,
)
from app.api.errors import internal_error

router = APIRouter()


@router.get("", response_model=List[MealResponseDTO])
def list_meals(
    name_pattern: Optional[str] = Query(None, description="Search by meal name"),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags"),
    saved: Optional[bool] = Query(None, description="Filter by saved status (true=saved, false=transient, omit=all)"),
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List meals with optional filters.

    Filters are stackable (AND logic):
    - name_pattern: Case-insensitive name search
    - tags: Comma-separated, meals must have ALL specified tags
    - saved: Filter by saved status (true=saved only, false=transient only)
    """
    # Parse tags if provided
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    filter_dto = MealFilterDTO(
        name_pattern=name_pattern,
        tags=tag_list,
        saved_only=saved,
        limit=limit,
        offset=offset,
    )

    service = MealService(session, current_user.id)
    return service.filter_meals(filter_dto)


@router.get("/by-recipe/{recipe_id}", response_model=List[MealResponseDTO])
def get_meals_by_recipe(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all meals that contain a specific recipe (main or side)."""
    service = MealService(session, current_user.id)
    return service.get_meals_by_recipe(recipe_id)


@router.get("/{meal_id}", response_model=MealResponseDTO)
def get_meal(
    meal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single meal by ID."""
    service = MealService(session, current_user.id)
    meal = service.get_meal(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return meal


@router.post("", response_model=MealResponseDTO, status_code=201)
def create_meal(
    meal_data: MealCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new meal.

    - meal_name: Required, 1-255 characters
    - main_recipe_id: Required, must exist
    - side_recipe_ids: Optional, max 3, maintains order
    - tags: Optional list of strings
    """
    service = MealService(session, current_user.id)
    try:
        return service.create_meal(meal_data)
    except InvalidRecipeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MealSaveError as e:
        raise internal_error()


@router.put("/{meal_id}", response_model=MealResponseDTO)
def update_meal(
    meal_id: int,
    update_data: MealUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update an existing meal."""
    service = MealService(session, current_user.id)
    try:
        meal = service.update_meal(meal_id, update_data)
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found")
        return meal
    except InvalidRecipeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MealSaveError as e:
        raise internal_error()


@router.delete("/{meal_id}")
def delete_meal(
    meal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a meal.

    Note: This will CASCADE delete any planner entries referencing this meal.
    """
    service = MealService(session, current_user.id)
    if not service.delete_meal(meal_id):
        raise HTTPException(status_code=404, detail="Meal not found")
    return {"message": "Meal deleted successfully"}


@router.post("/{meal_id}/save", response_model=MealResponseDTO)
def toggle_save(
    meal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Toggle the saved status of a meal.

    Saved meals persist permanently.
    Unsaved (transient) meals are deleted when they leave the planner.
    """
    service = MealService(session, current_user.id)
    meal = service.toggle_save(meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return meal


@router.post("/{meal_id}/sides/{recipe_id}", response_model=MealResponseDTO)
def add_side_recipe(
    meal_id: int,
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Add a side recipe to a meal.

    Maximum of 3 side recipes allowed.
    """
    service = MealService(session, current_user.id)
    try:
        meal = service.add_side_recipe(meal_id, recipe_id)
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found")
        return meal
    except InvalidRecipeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MealSaveError as e:
        raise internal_error()


@router.delete("/{meal_id}/sides/{recipe_id}", response_model=MealResponseDTO)
def remove_side_recipe(
    meal_id: int,
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove a side recipe from a meal."""
    service = MealService(session, current_user.id)
    try:
        meal = service.remove_side_recipe(meal_id, recipe_id)
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found")
        return meal
    except MealSaveError as e:
        raise internal_error()


@router.put("/{meal_id}/sides/reorder", response_model=MealResponseDTO)
def reorder_side_recipes(
    meal_id: int,
    side_recipe_ids: List[int],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder the side recipes of a meal.

    The provided list must contain the same recipe IDs as the current sides.
    """
    service = MealService(session, current_user.id)
    try:
        meal = service.reorder_side_recipes(meal_id, side_recipe_ids)
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found")
        return meal
    except InvalidRecipeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MealSaveError as e:
        raise internal_error()
