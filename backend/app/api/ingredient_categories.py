"""app/api/ingredient_categories.py

FastAPI router for user ingredient category endpoints.
Handles user ingredient category CRUD operations and management.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.user_ingredient_category_dtos import (
    UserIngredientCategoryBulkUpdateDTO,
    UserIngredientCategoryCreateDTO,
    UserIngredientCategoryReorderDTO,
    UserIngredientCategoryResponseDTO,
    UserIngredientCategoryUpdateDTO,
)
from app.models.user import User
from app.services.user_ingredient_category_service import (
    BuiltInIngredientCategoryError,
    IngredientCategoryLimitExceededError,
    DuplicateUserIngredientCategoryError,
    UserIngredientCategoryNotFoundError,
    UserIngredientCategorySaveError,
    UserIngredientCategoryService,
)
from app.api.errors import internal_error

router = APIRouter()


@router.get("", response_model=List[UserIngredientCategoryResponseDTO])
def list_ingredient_categories(
    include_disabled: bool = Query(False, description="Include disabled ingredient categories"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all ingredient categories for the current user.

    Returns ingredient categories ordered by position.
    On first access, built-in ingredient categories are automatically seeded.

    Query params:
    - include_disabled: If true, includes disabled ingredient categories (default: false)
    """
    service = UserIngredientCategoryService(session, current_user.id)
    return service.get_all_categories(include_disabled=include_disabled)


@router.get("/{category_id}", response_model=UserIngredientCategoryResponseDTO)
def get_ingredient_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single ingredient category by ID."""
    service = UserIngredientCategoryService(session, current_user.id)
    try:
        return service.get_category_by_id(category_id)
    except UserIngredientCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=UserIngredientCategoryResponseDTO, status_code=201)
def create_ingredient_category(
    category_data: UserIngredientCategoryCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new custom ingredient category.

    - label: Required, 1-50 characters
    - A URL-safe slug is automatically generated from the label
    - Maximum 50 custom ingredient categories per user
    """
    service = UserIngredientCategoryService(session, current_user.id)
    try:
        return service.create_category(category_data)
    except IngredientCategoryLimitExceededError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DuplicateUserIngredientCategoryError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except UserIngredientCategorySaveError as e:
        raise internal_error()


@router.put("/{category_id}", response_model=UserIngredientCategoryResponseDTO)
def update_ingredient_category(
    category_id: int,
    update_data: UserIngredientCategoryUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update an ingredient category.

    - label: Optional, 1-50 characters (only for custom ingredient categories)
    - is_enabled: Optional, toggle ingredient category visibility

    Note: Built-in ingredient categories can only be enabled/disabled, not renamed.
    """
    service = UserIngredientCategoryService(session, current_user.id)
    try:
        return service.update_category(category_id, update_data)
    except UserIngredientCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BuiltInIngredientCategoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserIngredientCategorySaveError as e:
        raise internal_error()


@router.delete("/{category_id}")
def delete_ingredient_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a custom ingredient category.

    Note: Built-in ingredient categories cannot be deleted, only disabled.
    """
    service = UserIngredientCategoryService(session, current_user.id)
    try:
        service.delete_category(category_id)
        return {"message": "Ingredient category deleted successfully"}
    except UserIngredientCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BuiltInIngredientCategoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserIngredientCategorySaveError as e:
        raise internal_error()


@router.put("/reorder", response_model=List[UserIngredientCategoryResponseDTO])
def reorder_ingredient_categories(
    reorder_data: UserIngredientCategoryReorderDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder ingredient categories.

    - ordered_ids: List of ingredient category IDs in the desired order
    """
    service = UserIngredientCategoryService(session, current_user.id)
    try:
        return service.reorder_categories(reorder_data)
    except UserIngredientCategorySaveError as e:
        raise internal_error()


@router.put("/bulk", response_model=List[UserIngredientCategoryResponseDTO])
def bulk_update_ingredient_categories(
    bulk_data: UserIngredientCategoryBulkUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk update multiple ingredient categories.

    - categories: List of {id, is_enabled, position} objects
    """
    service = UserIngredientCategoryService(session, current_user.id)
    try:
        return service.bulk_update(bulk_data)
    except UserIngredientCategorySaveError as e:
        raise internal_error()


@router.post("/reset", response_model=List[UserIngredientCategoryResponseDTO])
def reset_ingredient_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reset ingredient categories to defaults.

    - Re-enables all built-in ingredient categories
    - Disables (but keeps) all custom ingredient categories
    - Restores default ordering (built-ins first, then custom)
    """
    service = UserIngredientCategoryService(session, current_user.id)
    try:
        return service.reset_to_defaults()
    except UserIngredientCategorySaveError as e:
        raise internal_error()
