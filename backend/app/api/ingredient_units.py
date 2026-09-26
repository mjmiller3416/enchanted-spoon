"""app/api/ingredient_units.py

FastAPI router for user ingredient unit endpoints.
Handles user ingredient unit CRUD operations and management.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.user_ingredient_unit_dtos import (
    UserIngredientUnitBulkUpdateDTO,
    UserIngredientUnitCreateDTO,
    UserIngredientUnitReorderDTO,
    UserIngredientUnitResponseDTO,
    UserIngredientUnitUpdateDTO,
)
from app.models.user import User
from app.services.user_ingredient_unit_service import (
    BuiltInIngredientUnitError,
    DuplicateUserIngredientUnitError,
    IngredientUnitLimitExceededError,
    UserIngredientUnitNotFoundError,
    UserIngredientUnitSaveError,
    UserIngredientUnitService,
)
from app.api.errors import internal_error

router = APIRouter()


@router.get("", response_model=List[UserIngredientUnitResponseDTO])
def list_ingredient_units(
    include_disabled: bool = Query(False, description="Include disabled ingredient units"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all ingredient units for the current user.

    Returns ingredient units ordered by position.
    On first access, built-in units are automatically seeded.

    Query params:
    - include_disabled: If true, includes disabled units (default: false)
    """
    service = UserIngredientUnitService(session, current_user.id)
    return service.get_all_units(include_disabled=include_disabled)


@router.get("/{unit_id}", response_model=UserIngredientUnitResponseDTO)
def get_ingredient_unit(
    unit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single ingredient unit by ID."""
    service = UserIngredientUnitService(session, current_user.id)
    try:
        return service.get_unit_by_id(unit_id)
    except UserIngredientUnitNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=UserIngredientUnitResponseDTO, status_code=201)
def create_ingredient_unit(
    unit_data: UserIngredientUnitCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new custom ingredient unit.

    - label: Required, 1-50 characters
    - A URL-safe slug is automatically generated from the label
    - Custom units are always of type "count"
    - Maximum 50 custom units per user
    """
    service = UserIngredientUnitService(session, current_user.id)
    try:
        return service.create_unit(unit_data)
    except IngredientUnitLimitExceededError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DuplicateUserIngredientUnitError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except UserIngredientUnitSaveError as e:
        raise internal_error()


@router.put("/{unit_id}", response_model=UserIngredientUnitResponseDTO)
def update_ingredient_unit(
    unit_id: int,
    update_data: UserIngredientUnitUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update an ingredient unit.

    - label: Optional, 1-50 characters (only for custom units)
    - is_enabled: Optional, toggle unit visibility

    Note: Built-in units can only be enabled/disabled, not renamed.
    """
    service = UserIngredientUnitService(session, current_user.id)
    try:
        return service.update_unit(unit_id, update_data)
    except UserIngredientUnitNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BuiltInIngredientUnitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserIngredientUnitSaveError as e:
        raise internal_error()


@router.delete("/{unit_id}")
def delete_ingredient_unit(
    unit_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a custom ingredient unit.

    Note: Built-in units cannot be deleted, only disabled.
    """
    service = UserIngredientUnitService(session, current_user.id)
    try:
        service.delete_unit(unit_id)
        return {"message": "Ingredient unit deleted successfully"}
    except UserIngredientUnitNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BuiltInIngredientUnitError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserIngredientUnitSaveError as e:
        raise internal_error()


@router.put("/reorder", response_model=List[UserIngredientUnitResponseDTO])
def reorder_ingredient_units(
    reorder_data: UserIngredientUnitReorderDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder ingredient units.

    - ordered_ids: List of unit IDs in the desired order
    """
    service = UserIngredientUnitService(session, current_user.id)
    try:
        return service.reorder_units(reorder_data)
    except UserIngredientUnitSaveError as e:
        raise internal_error()


@router.put("/bulk", response_model=List[UserIngredientUnitResponseDTO])
def bulk_update_ingredient_units(
    bulk_data: UserIngredientUnitBulkUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk update multiple ingredient units.

    - units: List of {id, is_enabled, position} objects
    """
    service = UserIngredientUnitService(session, current_user.id)
    try:
        return service.bulk_update(bulk_data)
    except UserIngredientUnitSaveError as e:
        raise internal_error()


@router.post("/reset", response_model=List[UserIngredientUnitResponseDTO])
def reset_ingredient_units(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reset ingredient units to defaults.

    - Re-enables all built-in units
    - Disables (but keeps) all custom units
    - Restores default ordering (built-ins first, then custom)
    """
    service = UserIngredientUnitService(session, current_user.id)
    try:
        return service.reset_to_defaults()
    except UserIngredientUnitSaveError as e:
        raise internal_error()
