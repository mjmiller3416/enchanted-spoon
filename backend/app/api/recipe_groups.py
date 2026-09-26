"""app/api/recipe_groups.py

FastAPI router for recipe group endpoints.
Handles recipe group CRUD operations and recipe assignments.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.recipe_group_dtos import (
    RecipeGroupAssignmentDTO,
    RecipeGroupCreateDTO,
    RecipeGroupResponseDTO,
    RecipeGroupUpdateDTO,
)
from app.models.user import User
from app.services.recipe_group_service import (
    DuplicateRecipeGroupError,
    RecipeGroupNotFoundError,
    RecipeGroupSaveError,
    RecipeGroupService,
)
from app.api.errors import internal_error

router = APIRouter()


@router.get("", response_model=List[RecipeGroupResponseDTO])
def list_groups(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    List all recipe groups for the current user.

    Returns groups ordered alphabetically by name with recipe counts.
    """
    service = RecipeGroupService(session, current_user.id)
    return service.get_all_groups()


@router.get("/{group_id}", response_model=RecipeGroupResponseDTO)
def get_group(
    group_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single recipe group by ID."""
    service = RecipeGroupService(session, current_user.id)
    try:
        return service.get_group_by_id(group_id)
    except RecipeGroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=RecipeGroupResponseDTO, status_code=201)
def create_group(
    group_data: RecipeGroupCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new recipe group.

    - name: Required, 1-255 characters, must be unique per user (case-insensitive)
    """
    service = RecipeGroupService(session, current_user.id)
    try:
        return service.create_group(group_data)
    except DuplicateRecipeGroupError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RecipeGroupSaveError as e:
        raise internal_error()


@router.put("/{group_id}", response_model=RecipeGroupResponseDTO)
def update_group(
    group_id: int,
    update_data: RecipeGroupUpdateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Update a recipe group's name.

    - name: Required, 1-255 characters, must be unique per user (case-insensitive)
    """
    service = RecipeGroupService(session, current_user.id)
    try:
        return service.update_group(group_id, update_data)
    except RecipeGroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateRecipeGroupError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RecipeGroupSaveError as e:
        raise internal_error()


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a recipe group.

    Note: This only deletes the group, not the recipes within it.
    """
    service = RecipeGroupService(session, current_user.id)
    try:
        service.delete_group(group_id)
        return {"message": "Recipe group deleted successfully"}
    except RecipeGroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RecipeGroupSaveError as e:
        raise internal_error()


@router.get("/by-recipe/{recipe_id}", response_model=List[RecipeGroupResponseDTO])
def get_groups_for_recipe(
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all groups that contain a specific recipe."""
    service = RecipeGroupService(session, current_user.id)
    return service.get_groups_for_recipe(recipe_id)


@router.put("/by-recipe/{recipe_id}/assign", response_model=List[RecipeGroupResponseDTO])
def assign_recipe_to_groups(
    recipe_id: int,
    assignment_data: RecipeGroupAssignmentDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Assign a recipe to the specified groups (replaces existing assignments).

    - group_ids: List of group IDs to assign the recipe to
    """
    service = RecipeGroupService(session, current_user.id)
    try:
        return service.assign_recipe_to_groups(recipe_id, assignment_data)
    except RecipeGroupSaveError as e:
        raise internal_error()


@router.post("/{group_id}/recipes/{recipe_id}", response_model=RecipeGroupResponseDTO)
def add_recipe_to_group(
    group_id: int,
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Add a recipe to a group."""
    service = RecipeGroupService(session, current_user.id)
    try:
        return service.add_recipe_to_group(group_id, recipe_id)
    except RecipeGroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RecipeGroupSaveError as e:
        raise internal_error()


@router.delete("/{group_id}/recipes/{recipe_id}", response_model=RecipeGroupResponseDTO)
def remove_recipe_from_group(
    group_id: int,
    recipe_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove a recipe from a group."""
    service = RecipeGroupService(session, current_user.id)
    try:
        return service.remove_recipe_from_group(group_id, recipe_id)
    except RecipeGroupNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RecipeGroupSaveError as e:
        raise internal_error()
