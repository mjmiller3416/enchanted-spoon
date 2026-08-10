"""app/api/users.py

User profile API routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.admin_dtos import CurrentUserDTO, CurrentUserUsageDTO
from app.models.user import User
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
