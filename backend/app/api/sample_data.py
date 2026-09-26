"""app/api/sample_data.py

FastAPI router for the onboarding starter pack (sample recipes, meals,
planner entries, and the shopping list they produce).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.sample_data_dtos import (
    SampleDataRemovalResultDTO,
    SampleDataSeedResultDTO,
    SampleDataStatusDTO,
)
from app.models.user import User
from app.services.sample_data import (
    SampleDataAlreadyPresentError,
    SampleDataError,
    SampleDataService,
)
from app.api.errors import internal_error

router = APIRouter()


@router.get("", response_model=SampleDataStatusDTO)
def get_sample_data_status(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Whether the current user still has untouched sample content."""
    return SampleDataService(session, current_user.id).get_status()


@router.post("", response_model=SampleDataSeedResultDTO, status_code=201)
def add_sample_data(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Add the starter pack to the current account.

    Skips recipes the user already has and stops planning at planner capacity.
    """
    service = SampleDataService(session, current_user.id)
    try:
        return service.seed()
    except SampleDataAlreadyPresentError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SampleDataError as e:
        raise internal_error()


@router.delete("", response_model=SampleDataRemovalResultDTO)
def remove_sample_data(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Remove untouched sample recipes and meals (and their planner entries).

    Sample recipes the user edited, or uses in their own meals, are kept.
    """
    service = SampleDataService(session, current_user.id)
    try:
        return service.remove()
    except SampleDataError as e:
        raise internal_error()
