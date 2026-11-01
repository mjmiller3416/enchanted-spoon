"""app/api/recipes.py

FastAPI router for recipe endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.meal_dtos import RecipeDeletionImpactDTO
from app.models.user import User
from app.dtos.recipe_dtos import (
    RecipeCardDTO,
    RecipeCreateDTO,
    RecipeFilterDTO,
    RecipeResponseDTO,
    RecipeUpdateDTO,
)
from app.models.household import shared_recipe_id_select
from app.services.recipe_service import (
    DuplicateRecipeError,
    RecipeInUseError,
    RecipeNotFoundError,
    RecipeSaveError,
    RecipeService,
)
from app.api.errors import internal_error

router = APIRouter()


def _shared_ids(session: Session, user_id: int) -> set[int]:
    return set(session.scalars(shared_recipe_id_select(user_id)).all())


def _mark_visibility(dto, recipe, user_id: int, shared_ids: set[int]):
    """Mark household cookbook cards the caller can see but not edit."""
    if dto is None:
        return None
    dto.can_edit = recipe.user_id == user_id
    dto.shared_with_household = recipe.id in shared_ids
    return dto


@router.get("", response_model=List[RecipeResponseDTO])
def list_recipes(
    recipe_category: Optional[str] = Query(None),
    meal_type: Optional[str] = Query(None),
    diet_pref: Optional[str] = Query(None),
    cook_time: Optional[int] = Query(None, ge=0),
    servings: Optional[int] = Query(None, ge=1),
    sort_by: Optional[str] = Query(None, pattern="^(recipe_name|created_at|total_time|servings)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    favorites_only: bool = Query(False),
    search_term: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List recipes with optional filters."""
    filter_dto = RecipeFilterDTO(
        recipe_category=recipe_category,
        meal_type=meal_type,
        diet_pref=diet_pref,
        cook_time=cook_time,
        servings=servings,
        sort_by=sort_by,
        sort_order=sort_order,
        favorites_only=favorites_only,
        search_term=search_term,
        limit=limit,
        offset=offset,
    )

    service = RecipeService(session, current_user.id)
    recipes = service.list_filtered(filter_dto, include_shared=True)
    shared_ids = _shared_ids(session, current_user.id)
    return [
        _mark_visibility(RecipeResponseDTO.from_recipe(r), r, current_user.id, shared_ids)
        for r in recipes
    ]


@router.get("/cards", response_model=List[RecipeCardDTO])
def list_recipe_cards(
    recipe_category: Optional[str] = Query(None),
    meal_type: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    search_term: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List recipes as lightweight cards for lists/grids."""
    filter_dto = RecipeFilterDTO(
        recipe_category=recipe_category,
        meal_type=meal_type,
        favorites_only=favorites_only,
        search_term=search_term,
        limit=limit,
    )

    service = RecipeService(session, current_user.id)
    recipes = service.list_filtered(filter_dto, include_shared=True)
    shared_ids = _shared_ids(session, current_user.id)
    return [
        _mark_visibility(RecipeCardDTO.from_recipe(r), r, current_user.id, shared_ids)
        for r in recipes
    ]


@router.get("/categories", response_model=List[str])
def get_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get unique recipe categories."""
    service = RecipeService(session, current_user.id)
    recipes = service.list_filtered(RecipeFilterDTO(), include_shared=True)
    categories = set(r.recipe_category for r in recipes if r.recipe_category)
    return sorted(categories)


@router.get("/meal-types", response_model=List[str])
def get_meal_types(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get unique meal types."""
    service = RecipeService(session, current_user.id)
    recipes = service.list_filtered(RecipeFilterDTO(), include_shared=True)
    meal_types = set(r.meal_type for r in recipes if r.meal_type)
    return sorted(meal_types)


@router.get("/{recipe_id}/deletion-impact", response_model=RecipeDeletionImpactDTO)
def get_deletion_impact(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get the impact of deleting a recipe on meals.

    Returns:
    - meals_to_delete: Meals that will be deleted (recipe is their main)
    - meals_to_update: Meals that will have this recipe removed from sides
    """
    service = RecipeService(session, current_user.id)
    recipe = service.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return service.get_recipe_deletion_impact(recipe_id)


@router.get("/{recipe_id}/last-cooked")
def get_last_cooked(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get the most recent date a recipe was cooked."""
    service = RecipeService(session, current_user.id)
    recipe = service.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    last_cooked = service.get_last_cooked_date(recipe_id)
    return {"last_cooked": last_cooked.isoformat() if last_cooked else None}


@router.get("/{recipe_id}", response_model=RecipeResponseDTO)
def get_recipe(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single recipe by ID."""
    service = RecipeService(session, current_user.id)
    recipe = service.get_recipe(recipe_id, include_shared=True)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _mark_visibility(
        RecipeResponseDTO.from_recipe(recipe),
        recipe,
        current_user.id,
        _shared_ids(session, current_user.id),
    )


@router.post("", response_model=RecipeResponseDTO, status_code=201)
def create_recipe(
    recipe_data: RecipeCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new recipe."""
    service = RecipeService(session, current_user.id)
    try:
        recipe = service.create_recipe_with_ingredients(recipe_data)
        return RecipeResponseDTO.from_recipe(recipe)
    except DuplicateRecipeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RecipeSaveError as e:
        raise internal_error()


@router.put("/{recipe_id}", response_model=RecipeResponseDTO)
def update_recipe(
    recipe_id: int,
    update_data: RecipeUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update an existing recipe."""
    service = RecipeService(session, current_user.id)
    try:
        recipe = service.update_recipe(recipe_id, update_data)
        return RecipeResponseDTO.from_recipe(recipe)
    except RecipeNotFoundError:
        raise HTTPException(status_code=404, detail="Recipe not found")
    except RecipeSaveError:
        raise internal_error()


@router.delete("/{recipe_id}")
def delete_recipe(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a recipe."""
    service = RecipeService(session, current_user.id)
    try:
        deleted = service.delete_recipe(recipe_id)
    except RecipeInUseError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"message": "Recipe deleted successfully"}


@router.post("/{recipe_id}/favorite", response_model=RecipeResponseDTO)
def toggle_favorite(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Toggle the favorite status of a recipe."""
    service = RecipeService(session, current_user.id)
    recipe = service.get_recipe(recipe_id, include_shared=True)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the recipe owner can change it.")

    updated_recipe = service.toggle_favorite(recipe_id)
    if updated_recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return _mark_visibility(
        RecipeResponseDTO.from_recipe(updated_recipe),
        updated_recipe,
        current_user.id,
        _shared_ids(session, current_user.id),
    )
