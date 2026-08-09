"""Feedback API endpoint — creates a GitHub issue from user feedback."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.auth import get_current_user
from app.core.rate_limit import limiter
from app.dtos.feedback import FeedbackCreateDTO, FeedbackResponseDTO
from app.models.user import User
from app.services.github_service import GitHubIssueError, GitHubService

router = APIRouter()


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
            user_email=current_user.email,
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
