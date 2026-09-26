"""app/api/users.py

User profile API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.admin_dtos import CurrentUserDTO, CurrentUserUsageDTO
from app.api.errors import internal_error
from app.models.user import User
from app.services.account_service import (
    AccountDeletionBlockedError,
    AccountDeletionError,
    AccountService,
)
from app.services.usage_service import UsageService

router = APIRouter()


@router.get("/me", response_model=CurrentUserDTO)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> CurrentUserDTO:
    """Get the current user's profile including admin status."""
    return CurrentUserDTO.from_model(current_user)


@router.get("/me/usage", response_model=CurrentUserUsageDTO)
def get_current_user_usage(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CurrentUserUsageDTO:
    """Get the current month's AI usage counters and tier caps for the user.

    Backs the usage meter in Settings → Plan & Billing. Limits are ``None``
    for uncapped fields (admins are uncapped on everything).
    """
    usage = UsageService(session, current_user.id).get_usage()
    return CurrentUserUsageDTO.from_models(current_user, usage)


class AccountDeletionResultDTO(BaseModel):
    """Result of deleting the signed-in user's account."""

    deleted: bool
    # False when app data is gone but the sign-in identity couldn't be removed;
    # the client should sign the user out either way
    sign_in_deleted: bool


@router.delete("/me", response_model=AccountDeletionResultDTO)
def delete_current_user_account(
    confirm: bool = Query(False, description="Must be true; guards against accidental calls"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AccountDeletionResultDTO:
    """Permanently delete the signed-in user's account, data, and subscription."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Account deletion must be confirmed")
    try:
        sign_in_deleted = AccountService(session).delete_account(current_user)
    except AccountDeletionBlockedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except AccountDeletionError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        raise internal_error("Your account could not be deleted. Please try again.")
    return AccountDeletionResultDTO(deleted=True, sign_in_deleted=sign_in_deleted)
