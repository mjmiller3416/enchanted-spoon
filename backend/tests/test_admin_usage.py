"""Tests for the admin usage-by-user view (GitHub issue #165).

Covers:
- AdminService.get_usage_by_user — LEFT JOIN semantics, zeros for users with
  no usage row, values flowing through, per-month isolation, and per-tier
  limit resolution (admin uncapped, pro caps, free caps).
- GET /api/admin/usage — month param defaulting and regex validation (422).
"""

import itertools
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.admin import router as admin_router
from app.api.auth import require_admin
from app.core.usage_limits import TIER_USAGE_LIMITS
from app.database.db import get_session
from app.dtos.admin_dtos import AdminUsageResponseDTO
from app.models.user import User
from app.models.user_usage import UserUsage
from app.services.admin_service import AdminService

MONTH = "2026-08"

_user_seq = itertools.count(1)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_user(db_session: Session, **overrides) -> User:
    """Insert and return a user with unique clerk_id/email."""
    n = next(_user_seq)
    data = dict(
        clerk_id=f"clerk_usage_{n}",
        email=f"usage{n}@example.com",
        name=f"Usage User {n}",
        is_admin=False,
        subscription_tier="free",
        subscription_status="active",
    )
    data.update(overrides)
    user = User(**data)
    db_session.add(user)
    db_session.flush()
    return user


def _make_usage(db_session: Session, user: User, month: str, **counts) -> UserUsage:
    """Insert and return a UserUsage row for user+month."""
    data = dict(
        ai_images_generated=0,
        ai_suggestions_requested=0,
        ai_assistant_messages=0,
        recipes_created=0,
        recipes_imported=0,
    )
    data.update(counts)
    usage = UserUsage(user_id=user.id, month=month, **data)
    db_session.add(usage)
    db_session.flush()
    return usage


def _row_for(response, user_id: int):
    """Find the usage DTO for a given user_id in the response."""
    return next(u for u in response.users if u.user_id == user_id)


# ---------------------------------------------------------------------------
# Service: counters and LEFT JOIN semantics
# ---------------------------------------------------------------------------

class TestUsageCounters:
    def test_user_without_usage_row_gets_zeros(self, db_session: Session):
        user = _make_user(db_session, subscription_tier="pro")
        service = AdminService(db_session, current_user_id=user.id)

        response = service.get_usage_by_user(month=MONTH)

        row = _row_for(response, user.id)
        assert row.ai_images_generated == 0
        assert row.ai_suggestions_requested == 0
        assert row.ai_assistant_messages == 0
        assert row.recipes_imported == 0
        assert row.recipes_created == 0

    def test_usage_row_values_flow_through(self, db_session: Session):
        user = _make_user(db_session, subscription_tier="pro")
        _make_usage(
            db_session,
            user,
            MONTH,
            ai_images_generated=4,
            ai_suggestions_requested=7,
            ai_assistant_messages=12,
            recipes_imported=3,
            recipes_created=9,
        )
        service = AdminService(db_session, current_user_id=user.id)

        response = service.get_usage_by_user(month=MONTH)

        row = _row_for(response, user.id)
        assert row.ai_images_generated == 4
        assert row.ai_suggestions_requested == 7
        assert row.ai_assistant_messages == 12
        assert row.recipes_imported == 3
        assert row.recipes_created == 9

    def test_only_requested_month_is_counted(self, db_session: Session):
        user = _make_user(db_session, subscription_tier="pro")
        _make_usage(db_session, user, "2026-07", ai_images_generated=99)
        _make_usage(db_session, user, MONTH, ai_images_generated=5)
        service = AdminService(db_session, current_user_id=user.id)

        response = service.get_usage_by_user(month=MONTH)

        row = _row_for(response, user.id)
        assert response.month == MONTH
        assert row.ai_images_generated == 5

    def test_every_user_appears_sorted_by_id(self, db_session: Session):
        first = _make_user(db_session, subscription_tier="pro")
        second = _make_user(db_session, subscription_tier="pro")
        third = _make_user(db_session, subscription_tier="pro")
        # Only the middle user has a usage row for the month.
        _make_usage(db_session, second, MONTH, ai_assistant_messages=2)
        service = AdminService(db_session, current_user_id=first.id)

        response = service.get_usage_by_user(month=MONTH)

        returned_ids = [u.user_id for u in response.users]
        assert returned_ids == sorted(returned_ids)
        for user in (first, second, third):
            assert user.id in returned_ids
        assert _row_for(response, first.id).ai_assistant_messages == 0
        assert _row_for(response, second.id).ai_assistant_messages == 2


# ---------------------------------------------------------------------------
# Service: per-tier limit resolution
# ---------------------------------------------------------------------------

class TestUsageLimits:
    def test_admin_limits_all_null(self, db_session: Session):
        admin = _make_user(db_session, is_admin=True)
        service = AdminService(db_session, current_user_id=admin.id)

        row = _row_for(service.get_usage_by_user(month=MONTH), admin.id)

        assert row.is_admin is True
        assert row.has_pro_access is True
        assert row.limits.ai_images_generated is None
        assert row.limits.ai_suggestions_requested is None
        assert row.limits.ai_assistant_messages is None
        assert row.limits.recipes_imported is None

    def test_pro_user_gets_pro_caps(self, db_session: Session):
        # Non-admin with an active paid subscription -> has_pro_access True.
        user = _make_user(
            db_session,
            is_admin=False,
            subscription_tier="pro",
            subscription_status="active",
        )
        service = AdminService(db_session, current_user_id=user.id)

        row = _row_for(service.get_usage_by_user(month=MONTH), user.id)

        pro = TIER_USAGE_LIMITS["pro"]
        assert row.has_pro_access is True
        assert row.limits.ai_images_generated == pro["ai_images_generated"]
        assert row.limits.ai_suggestions_requested == pro["ai_suggestions_requested"]
        assert row.limits.ai_assistant_messages == pro["ai_assistant_messages"]
        assert row.limits.recipes_imported == pro["recipes_imported"]

    def test_free_user_gets_free_caps(self, db_session: Session):
        user = _make_user(db_session, is_admin=False, subscription_tier="free")
        service = AdminService(db_session, current_user_id=user.id)

        row = _row_for(service.get_usage_by_user(month=MONTH), user.id)

        free = TIER_USAGE_LIMITS["free"]
        assert row.has_pro_access is False
        assert row.limits.ai_images_generated == free["ai_images_generated"]
        assert row.limits.ai_suggestions_requested == free["ai_suggestions_requested"]
        assert row.limits.ai_assistant_messages == free["ai_assistant_messages"]
        assert row.limits.recipes_imported == free["recipes_imported"]

    def test_granted_pro_user_gets_pro_caps(self, db_session: Session):
        # has_pro_access can also come from a temporary grant (free tier still).
        from datetime import datetime, timedelta, timezone

        user = _make_user(
            db_session,
            is_admin=False,
            subscription_tier="free",
            granted_pro_until=datetime.now(timezone.utc) + timedelta(days=30),
            granted_by="test",
        )
        service = AdminService(db_session, current_user_id=user.id)

        row = _row_for(service.get_usage_by_user(month=MONTH), user.id)

        assert row.has_pro_access is True
        assert row.limits.ai_images_generated == TIER_USAGE_LIMITS["pro"][
            "ai_images_generated"
        ]


# ---------------------------------------------------------------------------
# Service: month defaulting
# ---------------------------------------------------------------------------

class TestMonthDefaulting:
    def test_defaults_to_current_utc_month(self, db_session: Session):
        user = _make_user(db_session, subscription_tier="pro")
        service = AdminService(db_session, current_user_id=user.id)

        response = service.get_usage_by_user()

        assert response.month == UserUsage.get_current_month()


# ---------------------------------------------------------------------------
# Route: month param validation and passthrough
#
# The service (exercised against a real DB above) owns the query and month
# defaulting; these route tests mock the service to verify wiring, regex
# validation, and that the raw `month` query param reaches the service.
# TestClient dispatches on a worker thread, so the thread-bound in-memory
# SQLite session cannot be shared into the request here.
# ---------------------------------------------------------------------------

def _admin_app(admin_user: User) -> FastAPI:
    """Mount the admin router with auth + session overridden."""
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/admin")
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[require_admin] = lambda: admin_user
    return app


def _fake_admin() -> User:
    user = MagicMock(spec=User)
    user.id = 1
    user.is_admin = True
    return user


class TestUsageEndpoint:
    @patch("app.api.admin.AdminService")
    def test_valid_month_returns_200(self, mock_service_cls):
        mock_service = MagicMock()
        mock_service.get_usage_by_user.return_value = AdminUsageResponseDTO(
            month=MONTH, users=[]
        )
        mock_service_cls.return_value = mock_service
        client = TestClient(_admin_app(_fake_admin()))

        response = client.get("/api/admin/usage", params={"month": MONTH})

        assert response.status_code == 200
        assert response.json()["month"] == MONTH
        mock_service.get_usage_by_user.assert_called_once_with(month=MONTH)

    @patch("app.api.admin.AdminService")
    def test_month_defaults_to_none_at_route(self, mock_service_cls):
        # When omitted, the route passes month=None; the service applies the
        # current-UTC-month default (covered by TestMonthDefaulting).
        mock_service = MagicMock()
        mock_service.get_usage_by_user.return_value = AdminUsageResponseDTO(
            month=UserUsage.get_current_month(), users=[]
        )
        mock_service_cls.return_value = mock_service
        client = TestClient(_admin_app(_fake_admin()))

        response = client.get("/api/admin/usage")

        assert response.status_code == 200
        mock_service.get_usage_by_user.assert_called_once_with(month=None)

    @pytest.mark.parametrize(
        "bad_month", ["2026-8", "August", "26-08", "2026/08", "2026-013"]
    )
    def test_bad_month_format_returns_422(self, bad_month: str):
        client = TestClient(_admin_app(_fake_admin()))

        response = client.get("/api/admin/usage", params={"month": bad_month})

        assert response.status_code == 422
