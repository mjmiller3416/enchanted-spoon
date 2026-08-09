"""app/api/ingredients.py

FastAPI router for ingredient endpoints.
All endpoints require authentication and are scoped to the current user.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.ingredient_dtos import (
    IngredientCreateDTO,
    IngredientResponseDTO,
    IngredientSearchDTO,
    IngredientUpdateDTO,
)
from app.models.user import User
from app.services.ingredient_service import IngredientNotFoundError, IngredientService

router = APIRouter()


def _ingredient_to_response_dto(ingredient) -> IngredientResponseDTO:
    """Convert an Ingredient model to IngredientResponseDTO."""
    return IngredientResponseDTO(
        id=ingredient.id,
        ingredient_name=ingredient.ingredient_name,
        ingredient_category=ingredient.ingredient_category,
    )


@router.get("", response_model=List[IngredientResponseDTO])
async def list_ingredients(
    search_term: Optional[str] = Query(None, min_length=1),
    category: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List or search ingredients for the current user."""
    service = IngredientService(session, current_user.id)

    if search_term:
        ingredients = service.search_ingredients(search_term, category)
    elif category:
        ingredients = service.get_ingredients_by_category(category)
    else:
        ingredients = service.get_all_ingredients()

    # Apply limit/offset if provided
    if offset:
        ingredients = ingredients[offset:]
    if limit:
        ingredients = ingredients[:limit]

    return [_ingredient_to_response_dto(ing) for ing in ingredients]


@router.get("/categories", response_model=List[str])
async def get_ingredient_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get unique ingredient categories for the current user."""
    service = IngredientService(session, current_user.id)
    return service.get_ingredient_categories()


@router.get("/names", response_model=List[str])
async def get_ingredient_names(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all unique ingredient names for autocomplete."""
    service = IngredientService(session, current_user.id)
    return service.list_all_ingredient_names()


@router.get("/{ingredient_id}", response_model=IngredientResponseDTO)
async def get_ingredient(
    ingredient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single ingredient by ID."""
    service = IngredientService(session, current_user.id)
    ingredient = service.get_ingredient_by_id(ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return _ingredient_to_response_dto(ingredient)


@router.post("", response_model=IngredientResponseDTO, status_code=201)
async def create_ingredient(
    ingredient_data: IngredientCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new ingredient or return existing one."""
    service = IngredientService(session, current_user.id)
    try:
        ingredient = service.create_ingredient(ingredient_data)
        return _ingredient_to_response_dto(ingredient)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=List[IngredientResponseDTO], status_code=201)
async def bulk_create_ingredients(
    ingredients_data: List[IngredientCreateDTO],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Bulk create ingredients. Returns existing ingredients if they already exist."""
    service = IngredientService(session, current_user.id)
    try:
        ingredients = service.bulk_create_ingredients(ingredients_data)
        return [_ingredient_to_response_dto(ing) for ing in ingredients]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{ingredient_id}", response_model=IngredientResponseDTO)
async def update_ingredient(
    ingredient_id: int,
    update_data: IngredientUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update an existing ingredient."""
    service = IngredientService(session, current_user.id)
    try:
        ingredient = service.update_ingredient(ingredient_id, update_data)
        return _ingredient_to_response_dto(ingredient)
    except IngredientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ingredient_id}")
async def delete_ingredient(
    ingredient_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete an ingredient."""
    service = IngredientService(session, current_user.id)
    try:
        service.delete_ingredient(ingredient_id)
        return {"message": "Ingredient deleted successfully"}
    except IngredientNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=List[IngredientResponseDTO])
async def search_ingredients(
    search_data: IngredientSearchDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Search ingredients using a search DTO."""
    service = IngredientService(session, current_user.id)
    ingredients = service.find_matching_ingredients(search_data)

    # Apply limit/offset if provided
    if search_data.offset:
        ingredients = ingredients[search_data.offset:]
    if search_data.limit:
        ingredients = ingredients[:search_data.limit]

    return [_ingredient_to_response_dto(ing) for ing in ingredients]
