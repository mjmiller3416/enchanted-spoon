"""app/services/usage_service.py

Service for tracking and checking feature usage limits.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from ..core.usage_limits import get_monthly_limit
from ..models.user_usage import UserUsage


class UsageLimitExceededError(Exception):
    """Raised when a user has reached their monthly cap for a usage field."""

    def __init__(self, field: str, limit: int, current: int):
        self.field = field
        self.limit = limit
        self.current = current
        super().__init__(f"Monthly limit reached for '{field}': {current}/{limit}")


class UsageService:
    """
    Service for tracking monthly feature usage.

    This service provides a simple interface for incrementing usage counters
    without the caller needing to manage UserUsage records directly.

    Capped AI features go through `reserve` (before the Gemini call) and
    `release` (if the call fails) so the cap is enforced atomically in the
    database: parallel requests can't each pass a stale check and overshoot.

    Usage:
        UsageService(session, user_id).increment("recipes_created")
    """

    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id
        self._reserved_month: Optional[str] = None

    def _get_current_month(self) -> str:
        """Get current month string in YYYY-MM format."""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _get_or_create_usage(self, month: Optional[str] = None) -> UserUsage:
        """
        Get or create usage record for user+month.

        Args:
            month: Month in YYYY-MM format. Defaults to current month.

        Returns:
            UserUsage record for the specified user and month.
        """
        if month is None:
            month = self._get_current_month()

        usage = self.session.query(UserUsage).filter(
            UserUsage.user_id == self.user_id,
            UserUsage.month == month
        ).first()

        if not usage:
            usage = UserUsage(user_id=self.user_id, month=month)
            self.session.add(usage)
            self.session.flush()

        return usage

    def _ensure_row(self, month: str) -> None:
        """Insert the user+month row if missing, tolerating a concurrent insert."""
        dialect = self.session.get_bind().dialect.name
        insert_fn = pg_insert if dialect == "postgresql" else sqlite_insert
        self.session.execute(
            insert_fn(UserUsage)
            .values(user_id=self.user_id, month=month)
            .on_conflict_do_nothing(index_elements=["user_id", "month"])
        )

    def _current_value(self, field: str, month: str) -> int:
        column = getattr(UserUsage, field)
        value = self.session.scalar(
            select(column).where(
                UserUsage.user_id == self.user_id, UserUsage.month == month
            )
        )
        return value or 0

    def increment(self, field: str, amount: int = 1) -> None:
        """
        Increment a usage counter atomically (no cap check).

        Args:
            field: Field name to increment. Valid fields:
                - 'ai_images_generated'
                - 'ai_suggestions_requested'
                - 'ai_assistant_messages'
                - 'recipes_created'
                - 'recipes_imported'
            amount: Amount to increment by (default 1)

        Raises:
            AttributeError: If field name is invalid
        """
        month = self._get_current_month()
        column = getattr(UserUsage, field)
        self._ensure_row(month)
        self.session.execute(
            update(UserUsage)
            .where(UserUsage.user_id == self.user_id, UserUsage.month == month)
            .values({field: column + amount})
            .execution_options(synchronize_session=False)
        )
        self.session.commit()

    def reserve(self, field: str, limit: Optional[int]) -> None:
        """
        Claim one unit of a capped feature before doing the work.

        The increment and the cap check are a single conditional UPDATE, so
        concurrent requests serialize on the row and at most `limit` succeed.
        Pair with `release` when the work fails so the user isn't charged.

        Args:
            field: Usage field to claim (see `increment` for valid fields).
            limit: Monthly cap for the user's tier, or None for uncapped
                (still counted, e.g. admins).

        Raises:
            UsageLimitExceededError: If the user has already reached `limit`.
        """
        month = self._get_current_month()
        column = getattr(UserUsage, field)
        self._ensure_row(month)

        stmt = update(UserUsage).where(
            UserUsage.user_id == self.user_id, UserUsage.month == month
        )
        if limit is not None:
            stmt = stmt.where(column < limit)
        result = self.session.execute(
            stmt.values({field: column + 1}).execution_options(
                synchronize_session=False
            )
        )

        if result.rowcount == 0:
            self.session.rollback()
            current = self._current_value(field, month)
            raise UsageLimitExceededError(field=field, limit=limit, current=current)

        self.session.commit()
        self._reserved_month = month

    def release(self, field: str) -> None:
        """
        Give back a unit claimed by `reserve` after the work failed.

        Rolls back first: the request that failed may have left the session
        mid-transaction, and nothing it did should be kept.
        """
        self.session.rollback()
        # Refund the month that was charged, even if the clock rolled over
        month = self._reserved_month or self._get_current_month()
        column = getattr(UserUsage, field)
        self.session.execute(
            update(UserUsage)
            .where(
                UserUsage.user_id == self.user_id,
                UserUsage.month == month,
                column > 0,
            )
            .values({field: column - 1})
            .execution_options(synchronize_session=False)
        )
        self.session.commit()

    def get_usage(self, month: Optional[str] = None) -> UserUsage:
        """
        Get usage record for a user (creates if doesn't exist).

        Args:
            month: Month in YYYY-MM format. Defaults to current month.

        Returns:
            UserUsage record for the specified user and month.
        """
        return self._get_or_create_usage(month)
