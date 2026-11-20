"""Feedback API endpoint — stores every submission, then tries a private issue."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.rate_limit import limiter
from app.core.stripe_config import get_stripe_settings
from app.database.db import get_session
from app.dtos.feedback import FeedbackCreateDTO, FeedbackResponseDTO
from app.models.user import User
from app.services.feedback_service import FeedbackSaveError, FeedbackService

router = APIRouter()


def _user_ref(user_id: int) -> str:
    """Opaque submitter reference plus an admin-only lookup link (no email)."""
    base_url = get_stripe_settings().frontend_url.rstrip("/")
    return f"user #{user_id} ([look up]({base_url}/admin?section=users&user={user_id}))"


@router.post("", response_model=FeedbackResponseDTO)
@limiter.limit("5/minute")
def submit_feedback(
    request: Request,
    feedback: FeedbackCreateDTO,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponseDTO:
    """Store feedback, then file a GitHub issue when the destination is private."""
    service = FeedbackService(session)
    try:
        return service.submit(
            user_id=current_user.id,
            feedback=feedback,
            user_ref=_user_ref(current_user.id),
        )
    except FeedbackSaveError:
        raise HTTPException(
            status_code=500,
            detail="We couldn't save your feedback. Please email info@enchantedspoon.app.",
        )
