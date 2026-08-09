"""Tests for UsageService.check_limit — monthly usage cap enforcement."""

from unittest.mock import MagicMock

import pytest

from app.models.user_usage import UserUsage
from app.services.usage_service import UsageLimitExceededError, UsageService


def _service_with_usage(**field_values) -> UsageService:
    """Build a UsageService whose session returns a pre-populated UserUsage row."""
    usage = UserUsage(user_id=1, month="2026-08")
    for field, value in field_values.items():
        setattr(usage, field, value)

    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = usage
    return UsageService(session, user_id=1)


class TestCheckLimitUnderCap:
    def test_allows_when_under_cap(self):
        service = _service_with_usage(ai_suggestions_requested=5)
        service.check_limit("ai_suggestions_requested", "pro")  # should not raise


class TestCheckLimitAtOrOverCap:
    def test_raises_when_at_cap(self):
        service = _service_with_usage(ai_images_generated=150)

        with pytest.raises(UsageLimitExceededError) as exc_info:
            service.check_limit("ai_images_generated", "pro")

        assert exc_info.value.field == "ai_images_generated"
        assert exc_info.value.limit == 150
        assert exc_info.value.current == 150

    def test_raises_when_over_cap(self):
        service = _service_with_usage(recipes_imported=999)

        with pytest.raises(UsageLimitExceededError):
            service.check_limit("recipes_imported", "pro")


class TestCheckLimitFreeTier:
    def test_free_tier_is_blocked_immediately(self):
        """Free tier has a 0 cap on AI fields today - any request is denied."""
        service = _service_with_usage(ai_suggestions_requested=0)

        with pytest.raises(UsageLimitExceededError):
            service.check_limit("ai_suggestions_requested", "free")


class TestCheckLimitUncappedField:
    def test_field_without_configured_limit_never_raises(self):
        service = _service_with_usage(recipes_created=999999)
        service.check_limit("recipes_created", "pro")  # uncapped, should not raise

    def test_unknown_tier_falls_back_to_free_caps(self):
        service = _service_with_usage(ai_suggestions_requested=0)

        with pytest.raises(UsageLimitExceededError):
            service.check_limit("ai_suggestions_requested", "some_future_tier")


class TestCheckLimitNewUser:
    def test_user_with_no_usage_row_yet_is_allowed(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.first.return_value = None
        service = UsageService(session, user_id=1)

        service.check_limit("ai_suggestions_requested", "pro")  # fresh row, should not raise
