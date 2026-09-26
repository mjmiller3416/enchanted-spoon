"""app/api/categories.py

FastAPI router for user category endpoints.
Handles user category CRUD operations and management.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.user_category_dtos import (
    UserCategoryBulkUpdateDTO,
    UserCategoryCreateDTO,
    UserCategoryReorderDTO,
    UserCategoryResponseDTO,
    UserCategoryUpdateDTO,
)
from app.models.user import User
from app.services.user_category_service import (
    BuiltInCategoryError,
    CategoryLimitExceededError,
    DuplicateUserCategoryError,
    UserCategoryNotFoundError,
    UserCategorySaveError,
    UserCategoryService,
)
from app.api.errors import internal_error

router = APIRouter()


@router.get("", response_model=List[UserCategoryResponseDTO])
def list_categories(
    include_disabled: bool = Query(False, description="Include disabled categories"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all categories for the current user.

    Returns categories ordered by position.
    On first access, built-in categories are automatically seeded.

    Query params:
    - include_disabled: If true, includes disabled categories (default: false)
    """
    service = UserCategoryService(session, current_user.id)
    return service.get_all_categories(include_disabled=include_disabled)


@router.get("/{category_id}", response_model=UserCategoryResponseDTO)
def get_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single category by ID."""
    service = UserCategoryService(session, current_user.id)
    try:
        return service.get_category_by_id(category_id)
    except UserCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=UserCategoryResponseDTO, status_code=201)
def create_category(
    category_data: UserCategoryCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new custom category.

    - label: Required, 1-50 characters
    - A URL-safe slug is automatically generated from the label
    - Maximum 50 custom categories per user
    """
    service = UserCategoryService(session, current_user.id)
    try:
        return service.create_category(category_data)
    except CategoryLimitExceededError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DuplicateUserCategoryError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except UserCategorySaveError as e:
        raise internal_error()


@router.put("/{category_id}", response_model=UserCategoryResponseDTO)
def update_category(
    category_id: int,
    update_data: UserCategoryUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update a category.

    - label: Optional, 1-50 characters (only for custom categories)
    - is_enabled: Optional, toggle category visibility

    Note: Built-in categories can only be enabled/disabled, not renamed.
    """
    service = UserCategoryService(session, current_user.id)
    try:
        return service.update_category(category_id, update_data)
    except UserCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BuiltInCategoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserCategorySaveError as e:
        raise internal_error()


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a custom category.

    Note: Built-in categories cannot be deleted, only disabled.
    """
    service = UserCategoryService(session, current_user.id)
    try:
        service.delete_category(category_id)
        return {"message": "Category deleted successfully"}
    except UserCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BuiltInCategoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserCategorySaveError as e:
        raise internal_error()


@router.put("/reorder", response_model=List[UserCategoryResponseDTO])
def reorder_categories(
    reorder_data: UserCategoryReorderDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder categories.

    - ordered_ids: List of category IDs in the desired order
    """
    service = UserCategoryService(session, current_user.id)
    try:
        return service.reorder_categories(reorder_data)
    except UserCategorySaveError as e:
        raise internal_error()


@router.put("/bulk", response_model=List[UserCategoryResponseDTO])
def bulk_update_categories(
    bulk_data: UserCategoryBulkUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk update multiple categories.

    - categories: List of {id, is_enabled, position} objects
    """
    service = UserCategoryService(session, current_user.id)
    try:
        return service.bulk_update(bulk_data)
    except UserCategorySaveError as e:
        raise internal_error()


@router.post("/reset", response_model=List[UserCategoryResponseDTO])
def reset_categories(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reset categories to defaults.

    - Re-enables all built-in categories
    - Disables (but keeps) all custom categories
    - Restores default ordering (built-ins first, then custom)
    """
    service = UserCategoryService(session, current_user.id)
    try:
        return service.reset_to_defaults()
    except UserCategorySaveError as e:
        raise internal_error()
