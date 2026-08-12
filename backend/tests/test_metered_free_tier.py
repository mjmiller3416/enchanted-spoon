"""Tests for the metered free tier (GitHub issue #164).

Covers:
- require_within_usage_limit — free users are metered against free caps
  instead of being blocked by the old binary pro gate: under-cap free users
  pass, at-cap free users get a structured 429, pro users get pro caps,
  admins are exempt entirely.
- GET /api/users/me/usage — the settings usage-meter endpoint: counters and
  per-tier limits for the signed-in user.

TestClient dispatches on a worker thread, so these tests use MagicMock
sessions (same pattern as the route tests in test_admin_usage.py) rather
than the thread-bound in-memory SQLite fixture.
"""

from unittest.mock import MagicMock

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.auth import get_current_user, require_within_usage_limit
from app.api.users import router as users_router
from app.core.usage_limits import TIER_USAGE_LIMITS
from app.database.db import get_session
from app.models.user import User
from app.models.user_usage import UserUsage

MONTH = "2026-08"

FREE_IMAGE_CAP = TIER_USAGE_LIMITS["free"]["ai_images_generated"]
PRO_IMAGE_CAP = TIER_USAGE_LIMITS["pro"]["ai_images_generated"]


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _user(**overrides) -> User:
    """Build a detached User (not persisted) so properties behave normally."""
    data = dict(
        id=1,
        clerk_id="clerk_metered_1",
        email="metered@example.com",
        name="Metered User",
        is_admin=False,
        subscription_tier="free",
        subscription_status="active",
    )
    data.update(overrides)
    return User(**data)


def _usage(**counts) -> UserUsage:
    usage = UserUsage(user_id=1, month=MONTH)
    for field, value in counts.items():
        setattr(usage, field, value)
    return usage


def _session_returning(usage: UserUsage) -> MagicMock:
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = usage
    return session


def _gated_app(user: User, usage: UserUsage) -> TestClient:
    """Mount a route gated by require_within_usage_limit with overrides."""
    app = FastAPI()

    @app.post("/gated")
    def gated(
        current_user: User = Depends(
            require_within_usage_limit("ai_images_generated")
        ),
    ):
        return {"ok": True}

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = lambda: _session_returning(usage)
    return TestClient(app)


# ---------------------------------------------------------------------------
# require_within_usage_limit — metered free tier
# ---------------------------------------------------------------------------

class TestFreeUserMetering:
    def test_free_user_under_cap_is_allowed(self):
        client = _gated_app(_user(), _usage(ai_images_generated=0))

        assert client.post("/gated").status_code == 200

    def test_free_user_at_cap_gets_structured_429(self):
        client = _gated_app(_user(), _usage(ai_images_generated=FREE_IMAGE_CAP))

        response = client.post("/gated")

        assert response.status_code == 429
        detail = response.json()["detail"]
        assert detail["error"] == "usage_limit_exceeded"
        assert detail["field"] == "ai_images_generated"
        assert detail["current"] == FREE_IMAGE_CAP
        assert detail["limit"] == FREE_IMAGE_CAP

    def test_free_user_is_not_403_blocked(self):
        """The old binary pro gate must not fire — free users are metered."""
        client = _gated_app(_user(), _usage(ai_images_generated=FREE_IMAGE_CAP))

        assert client.post("/gated").status_code != 403


class TestProUserMetering:
    def test_pro_user_over_free_cap_is_allowed(self):
        user = _user(subscription_tier="pro", subscription_status="active")
        client = _gated_app(user, _usage(ai_images_generated=FREE_IMAGE_CAP + 1))

        assert client.post("/gated").status_code == 200

    def test_pro_user_at_pro_cap_gets_429(self):
        user = _user(subscription_tier="pro", subscription_status="active")
        client = _gated_app(user, _usage(ai_images_generated=PRO_IMAGE_CAP))

        response = client.post("/gated")

        assert response.status_code == 429
        assert response.json()["detail"]["limit"] == PRO_IMAGE_CAP


class TestAdminExemption:
    def test_admin_is_never_capped(self):
        user = _user(is_admin=True)
        client = _gated_app(user, _usage(ai_images_generated=999_999))

        assert client.post("/gated").status_code == 200


# ---------------------------------------------------------------------------
# GET /api/users/me/usage — settings usage meter
# ---------------------------------------------------------------------------

def _users_app(user: User, usage: UserUsage) -> TestClient:
    app = FastAPI()
    app.include_router(users_router, prefix="/api/users")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = lambda: _session_returning(usage)
    return TestClient(app)


class TestCurrentUserUsageEndpoint:
    def test_free_user_gets_counters_and_free_caps(self):
        client = _users_app(
            _user(), _usage(ai_images_generated=2, ai_assistant_messages=4)
        )

        response = client.get("/api/users/me/usage")

        assert response.status_code == 200
        body = response.json()
        assert body["month"] == MONTH
        assert body["ai_images_generated"] == 2
        assert body["ai_assistant_messages"] == 4
        assert body["limits"] == {
            field: TIER_USAGE_LIMITS["free"][field]
            for field in (
                "ai_images_generated",
                "ai_suggestions_requested",
                "ai_assistant_messages",
                "recipes_imported",
            )
        }

    def test_pro_user_gets_pro_caps(self):
        user = _user(subscription_tier="pro", subscription_status="active")
        client = _users_app(user, _usage())

        body = client.get("/api/users/me/usage").json()

        assert body["limits"]["ai_images_generated"] == PRO_IMAGE_CAP

    def test_admin_limits_all_null(self):
        client = _users_app(_user(is_admin=True), _usage())

        body = client.get("/api/users/me/usage").json()

        assert all(v is None for v in body["limits"].values())
