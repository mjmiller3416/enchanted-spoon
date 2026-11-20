"""Data access for stored feedback. Flushes only; FeedbackService commits."""

from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.feedback import Feedback


class FeedbackRepository:
    """Reads and writes feedback rows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, feedback: Feedback) -> Feedback:
        """Stage a new row and flush so it has an id."""
        self.session.add(feedback)
        self.session.flush()
        return feedback

    def list_recent(self, skip: int, limit: int) -> Tuple[List[Feedback], int]:
        """Newest submissions first, plus the total count."""
        total = self.session.scalar(select(func.count()).select_from(Feedback)) or 0
        rows = list(
            self.session.scalars(
                select(Feedback)
                .order_by(Feedback.created_at.desc(), Feedback.id.desc())
                .offset(skip)
                .limit(limit)
            )
        )
        return rows, int(total)
