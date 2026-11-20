"""Accept feedback into the database, then try a private GitHub issue.

There is no outbound mailer in this app, so a stored submission is not also
emailed. Operators read the ``feedback`` table (admin list or SQL).
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..dtos.feedback import (
    AdminFeedbackItemDTO,
    AdminFeedbackListDTO,
    FeedbackCreateDTO,
    FeedbackResponseDTO,
)
from ..models.feedback import Feedback
from ..repositories.feedback_repo import FeedbackRepository
from .github_service import GitHubIssueError, GitHubService

logger = logging.getLogger(__name__)

STORED_MESSAGE = "Thanks! We got your feedback."
TRACKER_MESSAGE = "Thank you for your feedback! It has been submitted successfully."
DELIVERY_STORED = "stored"
DELIVERY_TRACKER = "tracker"


class FeedbackSaveError(Exception):
    """The feedback row itself could not be saved."""


class FeedbackService:
    """Persists every submission, then publishes only to a private tracker."""

    def __init__(self, session: Session, github: Optional[GitHubService] = None) -> None:
        self.session = session
        self.repo = FeedbackRepository(session)
        self.github = github or GitHubService()

    def submit(
        self,
        user_id: int,
        feedback: FeedbackCreateDTO,
        user_ref: str,
    ) -> FeedbackResponseDTO:
        """Save first. A tracker failure still returns success."""
        record = Feedback(
            user_id=user_id,
            category=feedback.category,
            message=feedback.message,
            metadata_json=dict(feedback.metadata) if feedback.metadata else None,
            delivery_status=DELIVERY_STORED,
        )
        try:
            self.repo.add(record)
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.warning("Feedback save failed: %s", type(exc).__name__)
            raise FeedbackSaveError("Failed to store feedback") from exc

        issue_url, error_reason = self._try_tracker(feedback, user_ref)
        if issue_url:
            record.delivery_status = DELIVERY_TRACKER
            record.issue_url = issue_url
            record.error_reason = None
            message = TRACKER_MESSAGE
        else:
            record.delivery_status = DELIVERY_STORED
            record.issue_url = None
            record.error_reason = error_reason
            message = STORED_MESSAGE
        self._commit_status(record)
        return FeedbackResponseDTO(success=True, message=message, issue_url=issue_url)

    def list_recent(self, skip: int, limit: int) -> AdminFeedbackListDTO:
        """Admin read of stored submissions. Does not commit."""
        rows, total = self.repo.list_recent(skip, limit)
        items = [
            AdminFeedbackItemDTO(
                id=row.id,
                user_id=row.user_id,
                category=row.category,
                message=row.message,
                metadata=row.metadata_json if isinstance(row.metadata_json, dict) else None,
                created_at=row.created_at,
                delivery_status=row.delivery_status,
                issue_url=row.issue_url,
                error_reason=row.error_reason,
            )
            for row in rows
        ]
        return AdminFeedbackListDTO(items=items, total=total)

    def _try_tracker(
        self,
        feedback: FeedbackCreateDTO,
        user_ref: str,
    ) -> tuple[Optional[str], Optional[str]]:
        """Return ``(issue_url, None)`` or ``(None, short_code)``."""
        try:
            issue_url = self.github.create_issue(
                category=feedback.category,
                message=feedback.message,
                user_ref=user_ref,
                metadata=feedback.metadata,
            )
        except GitHubIssueError as exc:
            return None, exc.code
        except Exception:
            # Class name only: exception text can echo the request body.
            logger.warning("Feedback tracker skipped: tracker_error")
            return None, "tracker_error"
        if not issue_url:
            logger.warning("Feedback tracker skipped: tracker_error")
            return None, "tracker_error"
        return issue_url, None

    def _commit_status(self, record: Feedback) -> None:
        """Record where the submission landed. The row already exists."""
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            logger.warning(
                "Feedback delivery status update failed id=%s error=%s",
                record.id,
                type(exc).__name__,
            )
