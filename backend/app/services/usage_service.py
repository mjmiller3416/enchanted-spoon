"""app/services/usage_service.py

Service for tracking and checking feature usage limits.
"""

from datetime import datetime, timezone
from typing import Optional

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

    Usage:
        UsageService(session, user_id).increment("ai_images_generated")
    """

    def __init__(self, session: Session, user_id: int):
        self.session = session
        self.user_id = user_id

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

    def increment(self, field: str, amount: int = 1) -> UserUsage:
        """
        Increment a usage counter.

        Args:
            field: Field name to increment. Valid fields:
                - 'ai_images_generated'
                - 'ai_suggestions_requested'
                - 'ai_assistant_messages'
                - 'recipes_created'
                - 'recipes_imported'
            amount: Amount to increment by (default 1)

        Returns:
            Updated UserUsage record

        Raises:
            AttributeError: If field name is invalid
        """
        usage = self._get_or_create_usage()
        current_value = getattr(usage, field, 0)
        setattr(usage, field, current_value + amount)
        self.session.commit()
        return usage

    def get_usage(self, month: Optional[str] = None) -> UserUsage:
        """
        Get usage record for a user (creates if doesn't exist).

        Args:
            month: Month in YYYY-MM format. Defaults to current month.

        Returns:
            UserUsage record for the specified user and month.
        """
        return self._get_or_create_usage(month)

    def check_limit(self, field: str, tier: str) -> None:
        """
        Raise UsageLimitExceededError if the user is at/over their monthly cap.

        Args:
            field: Usage field to check (see `increment` for valid fields).
            tier: Subscription tier to check the cap for (e.g. "pro", "free").

        Raises:
            UsageLimitExceededError: If the user has reached their monthly cap.
        """
        limit = get_monthly_limit(tier, field)
        if limit is None:
            return

        usage = self.get_usage()
        current = getattr(usage, field, 0) or 0
        if current >= limit:
            raise UsageLimitExceededError(field=field, limit=limit, current=current)
