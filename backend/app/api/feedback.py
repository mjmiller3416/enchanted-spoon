"""Feedback API endpoint — creates a GitHub issue from user feedback."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.auth import get_current_user
from app.core.rate_limit import limiter
from app.core.stripe_config import get_stripe_settings
from app.dtos.feedback import FeedbackCreateDTO, FeedbackResponseDTO
from app.models.user import User
from app.services.github_service import GitHubIssueError, GitHubService

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
    current_user: User = Depends(get_current_user),
) -> FeedbackResponseDTO:
    """Submit user feedback as a GitHub issue."""
    service = GitHubService()
    try:
        issue_url = service.create_issue(
            category=feedback.category,
            message=feedback.message,
            user_ref=_user_ref(current_user.id),
            metadata=feedback.metadata,
        )
        return FeedbackResponseDTO(
            success=True,
            message="Thank you for your feedback! It has been submitted successfully.",
            issue_url=issue_url,
        )
    except GitHubIssueError:
        raise HTTPException(
            status_code=502,
            detail="Failed to submit feedback. Please try again.",
        )
