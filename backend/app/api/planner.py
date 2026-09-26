"""app/api/planner.py

FastAPI router for planner endpoints.
Handles planner entry operations (adding/removing meals from planner).
Meal CRUD is handled by the meals router.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.planner_dtos import (
    CookingStreakDTO,
    PlannerShoppingModeDTO,
    PlannerBulkAddDTO,
    PlannerEntryResponseDTO,
    PlannerOperationResultDTO,
    PlannerReorderDTO,
    PlannerSummaryDTO,
)
from app.models.user import User
from app.services.planner import (
    InvalidMealError,
    PlannerFullError,
    PlannerService,
)

from app.services.planner.entry import EntryNotFoundError
from app.services.planner.status import ShoppingModeSaveError
from app.api.errors import internal_error

router = APIRouter()


# -- Read Operations -----------------------------------------------------------------------------
@router.get("/entries", response_model=List[PlannerEntryResponseDTO])
def get_all_entries(
    meal_id: Optional[int] = Query(None, description="Filter by meal ID"),
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get planner entries with optional filtering.

    - **meal_id**: Filter entries for a specific meal
    - **completed**: Filter by completion status (true/false)
    """
    service = PlannerService(session, current_user.id)
    return service.get_all_entries(meal_id=meal_id, completed=completed)


@router.get("/entries/{entry_id}", response_model=PlannerEntryResponseDTO)
def get_entry(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a single planner entry by ID."""
    service = PlannerService(session, current_user.id)
    entry = service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Planner entry not found")
    return entry


@router.get("/summary", response_model=PlannerSummaryDTO)
def get_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get a summary of the current planner state."""
    service = PlannerService(session, current_user.id)
    return service.get_summary()


@router.get("/meal-ids", response_model=List[int])
def get_meal_ids(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all meal IDs currently in the planner."""
    service = PlannerService(session, current_user.id)
    return service.get_meal_ids()


@router.get("/streak", response_model=CookingStreakDTO)
def get_cooking_streak(
    tz: Optional[str] = Query(None, description="User's IANA timezone (e.g., 'America/New_York')"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Get cooking streak information.

    Returns the current consecutive day streak, longest streak ever,
    and activity for the current calendar week (Monday-Sunday).

    The tz parameter ensures dates are calculated in the user's timezone.
    """
    service = PlannerService(session, current_user.id)
    return service.get_cooking_streak(user_timezone=tz)


# -- Add Operations ------------------------------------------------------------------------------
@router.post("/entries/{meal_id}", response_model=PlannerEntryResponseDTO, status_code=201)
def add_meal_to_planner(
    meal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Add a meal to the planner.

    Creates a new planner entry referencing the meal.
    The meal must exist. Maximum 15 entries allowed.
    """
    service = PlannerService(session, current_user.id)
    try:
        return service.add_meal_to_planner(meal_id)
    except PlannerFullError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidMealError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise internal_error()


@router.post("/entries/bulk", response_model=List[PlannerEntryResponseDTO], status_code=201)
def add_meals_to_planner(
    data: PlannerBulkAddDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Add multiple meals to the planner.

    All meals must exist. Total entries cannot exceed 15.
    """
    service = PlannerService(session, current_user.id)
    try:
        return service.add_meals_to_planner(data.meal_ids)
    except PlannerFullError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidMealError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise internal_error()


# -- Update Operations ---------------------------------------------------------------------------
@router.put("/entries/reorder", response_model=PlannerOperationResultDTO)
def reorder_entries(
    data: PlannerReorderDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder planner entries.

    Provide entry IDs in the desired order. Positions will be reassigned 0, 1, 2, ...
    """
    service = PlannerService(session, current_user.id)
    success = service.reorder_entries(data.entry_ids)
    return PlannerOperationResultDTO(
        success=success,
        message="Entries reordered successfully" if success else "Failed to reorder entries",
        affected_count=len(data.entry_ids) if success else 0,
    )


@router.post("/entries/{entry_id}/complete", response_model=PlannerEntryResponseDTO)
def mark_completed(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark a planner entry as completed."""
    service = PlannerService(session, current_user.id)
    entry = service.mark_completed(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Planner entry not found")
    return entry


@router.post("/entries/{entry_id}/incomplete", response_model=PlannerEntryResponseDTO)
def mark_incomplete(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Mark a planner entry as incomplete."""
    service = PlannerService(session, current_user.id)
    entry = service.mark_incomplete(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Planner entry not found")
    return entry


@router.put("/entries/{entry_id}/shopping-mode", response_model=PlannerEntryResponseDTO)
def set_shopping_mode(
    entry_id: int,
    data: PlannerShoppingModeDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PlannerEntryResponseDTO:
    service = PlannerService(session, current_user.id)
    try:
        return service.set_shopping_mode(entry_id, data)
    except EntryNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ShoppingModeSaveError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/entries/{entry_id}/cycle-shopping-mode", response_model=PlannerEntryResponseDTO)
def cycle_shopping_mode(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Cycle the shopping mode of a planner entry.

    Cycles through: all -> produce_only -> none -> all
    - all: Include all ingredients in shopping list
    - produce_only: Include only produce category ingredients
    - none: Exclude from shopping list entirely
    """
    service = PlannerService(session, current_user.id)
    entry = service.cycle_shopping_mode(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Planner entry not found")
    return entry


# -- Remove Operations ---------------------------------------------------------------------------
@router.delete("/entries/{entry_id}")
def remove_entry(
    entry_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a planner entry.

    Note: This does NOT delete the underlying meal.
    The meal can be re-added to the planner later.
    """
    service = PlannerService(session, current_user.id)
    if not service.remove_entry(entry_id):
        raise HTTPException(status_code=404, detail="Planner entry not found")
    return {"message": "Entry removed from planner"}


@router.delete("/entries/by-meal/{meal_id}")
def remove_entries_by_meal(
    meal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove all planner entries for a specific meal."""
    service = PlannerService(session, current_user.id)
    count = service.remove_entries_by_meal(meal_id)
    return {"message": f"Removed {count} entries for meal {meal_id}"}


@router.delete("/clear")
def clear_planner(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Clear all entries from the planner."""
    service = PlannerService(session, current_user.id)
    count = service.clear_planner()
    return {"message": f"Cleared {count} entries from planner"}


@router.delete("/clear-completed")
def clear_completed(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Clear all completed entries from the planner."""
    service = PlannerService(session, current_user.id)
    count = service.clear_completed()
    return {"message": f"Cleared {count} completed entries from planner"}
