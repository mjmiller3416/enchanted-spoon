"""Tests for UsageService — atomic monthly usage reservation.

Uses the file-backed `file_db` fixture: `reserve` commits and rolls back for
real, and the concurrency test needs one connection per thread.
"""

import threading

import pytest

from app.core.usage_limits import get_monthly_limit
from app.models.user_usage import UserUsage
from app.services.usage_service import UsageLimitExceededError, UsageService


def _seed(file_db, **counts) -> None:
    with file_db() as session:
        session.add(UserUsage(user_id=1, month=UserUsage.get_current_month(), **counts))
        session.commit()


def _count(file_db, field: str) -> int:
    with file_db() as session:
        usage = session.query(UserUsage).filter_by(user_id=1).first()
        return getattr(usage, field) if usage else 0


def _reserve(file_db, field: str, limit) -> None:
    with file_db() as session:
        UsageService(session, user_id=1).reserve(field, limit)


class TestReserve:
    def test_under_cap_claims_one_unit(self, file_db):
        _seed(file_db, ai_suggestions_requested=5)

        _reserve(file_db, "ai_suggestions_requested", 300)

        assert _count(file_db, "ai_suggestions_requested") == 6

    def test_new_user_gets_a_row(self, file_db):
        _reserve(file_db, "ai_images_generated", 3)

        assert _count(file_db, "ai_images_generated") == 1

    def test_at_cap_raises_without_counting(self, file_db):
        _seed(file_db, ai_images_generated=150)

        with pytest.raises(UsageLimitExceededError) as exc_info:
            _reserve(file_db, "ai_images_generated", 150)

        assert exc_info.value.field == "ai_images_generated"
        assert exc_info.value.limit == 150
        assert exc_info.value.current == 150
        assert _count(file_db, "ai_images_generated") == 150

    def test_over_cap_raises(self, file_db):
        _seed(file_db, recipes_imported=999)

        with pytest.raises(UsageLimitExceededError):
            _reserve(file_db, "recipes_imported", 100)

    def test_free_tier_cap(self, file_db):
        cap = get_monthly_limit("free", "ai_suggestions_requested")
        _seed(file_db, ai_suggestions_requested=cap - 1)

        _reserve(file_db, "ai_suggestions_requested", cap)
        with pytest.raises(UsageLimitExceededError):
            _reserve(file_db, "ai_suggestions_requested", cap)

        assert _count(file_db, "ai_suggestions_requested") == cap

    def test_uncapped_still_counts(self, file_db):
        _seed(file_db, recipes_created=999_999)

        _reserve(file_db, "recipes_created", None)

        assert _count(file_db, "recipes_created") == 1_000_000

    def test_concurrent_reservations_never_exceed_cap(self, file_db):
        cap = 3
        results: list[bool] = []
        barrier = threading.Barrier(10)

        def worker() -> None:
            barrier.wait()
            try:
                _reserve(file_db, "ai_images_generated", cap)
                results.append(True)
            except UsageLimitExceededError:
                results.append(False)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert results.count(True) == cap
        assert _count(file_db, "ai_images_generated") == cap


class TestRelease:
    def test_refunds_a_reserved_unit(self, file_db):
        _seed(file_db, ai_assistant_messages=2)
        with file_db() as session:
            service = UsageService(session, user_id=1)
            service.reserve("ai_assistant_messages", 10)
            service.release("ai_assistant_messages")

        assert _count(file_db, "ai_assistant_messages") == 2

    def test_never_goes_negative(self, file_db):
        _seed(file_db, ai_assistant_messages=0)
        with file_db() as session:
            UsageService(session, user_id=1).release("ai_assistant_messages")

        assert _count(file_db, "ai_assistant_messages") == 0


class TestIncrement:
    def test_increments_without_cap(self, file_db):
        with file_db() as session:
            service = UsageService(session, user_id=1)
            service.increment("recipes_created")
            service.increment("recipes_created", 2)

        assert _count(file_db, "recipes_created") == 3


def test_unknown_tier_falls_back_to_free_caps():
    assert get_monthly_limit("some_future_tier", "ai_suggestions_requested") == (
        get_monthly_limit("free", "ai_suggestions_requested")
    )
