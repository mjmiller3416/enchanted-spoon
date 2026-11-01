"""app/api/users.py

User profile API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.admin_dtos import AdminUsageLimitsDTO, CurrentUserDTO, CurrentUserUsageDTO
from app.api.errors import internal_error
from app.models.user import User
from app.services.account_service import (
    AccountDeletionBlockedError,
    AccountDeletionError,
    AccountService,
)
from app.services.household.scope import effective_access
from app.services.household.usage_meter import resolve_usage_meter
from app.services.usage_service import UsageService

router = APIRouter()


@router.get("/me", response_model=CurrentUserDTO)
def get_current_user_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CurrentUserDTO:
    """Get the current user's profile including admin status.

    ``has_pro_access`` is true when the household owner covers this member.
    """
    has_pro, reason = effective_access(session, current_user)
    return CurrentUserDTO.from_model(
        current_user, has_pro_access=has_pro, access_reason=reason
    )


@router.get("/me/usage", response_model=CurrentUserUsageDTO)
def get_current_user_usage(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CurrentUserUsageDTO:
    """Get the current month's AI usage counters and caps for the user.

    In a household of two or more, the counters and caps are the owner's
    shared pool (Pro caps × 1.5). Otherwise they are this user's own tier.
    """
    meter = resolve_usage_meter(session, current_user)
    usage = UsageService(session, meter.user_id).get_usage()
    has_pro, _reason = effective_access(session, current_user)
    limits = None
    if meter.shared:
        limits = AdminUsageLimitsDTO(
            ai_images_generated=meter.limit_for("ai_images_generated"),
            ai_suggestions_requested=meter.limit_for("ai_suggestions_requested"),
            ai_assistant_messages=meter.limit_for("ai_assistant_messages"),
            recipes_imported=meter.limit_for("recipes_imported"),
        )
    return CurrentUserUsageDTO.from_models(
        current_user,
        usage,
        has_pro_access=has_pro,
        limits=limits,
        shared_with_household=meter.shared,
    )


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
