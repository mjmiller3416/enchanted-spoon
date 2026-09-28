"""Tests for the admin activity-by-user view and last-active stamping.

Covers:
- UserService.touch_last_active — first stamp, throttling, re-stamp after the
  resolution window, naive (SQLite) timestamps, and updated_at left untouched.
- AdminService.get_activity_by_user — zeros for users with no data, starter
  pack exclusion, planner/cooking counts, recent-window counts, and summary.
- GET /api/admin/activity — wiring.
"""

import itertools
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.admin import router as admin_router
from app.api.auth import require_admin
from app.database.db import get_session
from app.dtos.admin_dtos import AdminActivityResponseDTO, AdminActivitySummaryDTO
from app.models.meal import Meal
from app.models.planner_entry import PlannerEntry
from app.models.recipe import Recipe
from app.models.recipe_group import RecipeGroup
from app.models.shopping_item import ShoppingItem
from app.models.user import User
from app.services.admin_service import AdminService
from app.services.user_service import LAST_ACTIVE_RESOLUTION, UserService

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)

_seq = itertools.count(1)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_user(db_session: Session, **overrides) -> User:
    n = next(_seq)
    data = dict(
        clerk_id=f"clerk_activity_{n}",
        email=f"activity{n}@example.com",
        name=f"Activity User {n}",
        is_admin=False,
        subscription_tier="free",
        subscription_status="active",
    )
    data.update(overrides)
    user = User(**data)
    db_session.add(user)
    db_session.flush()
    return user


def _make_recipe(db_session: Session, user: User, **overrides) -> Recipe:
    data = dict(
        recipe_name=f"Recipe {next(_seq)}",
        recipe_category="Dinner",
        meal_type="Dinner",
        user_id=user.id,
        created_at=NOW - timedelta(days=60),
    )
    data.update(overrides)
    recipe = Recipe(**data)
    db_session.add(recipe)
    db_session.flush()
    return recipe


def _make_meal(db_session: Session, user: User, recipe: Recipe, **overrides) -> Meal:
    data = dict(meal_name="Meal", main_recipe_id=recipe.id, user_id=user.id, is_saved=True)
    data.update(overrides)
    meal = Meal(**data)
    db_session.add(meal)
    db_session.flush()
    return meal


def _make_entry(db_session: Session, user: User, meal: Meal, **overrides) -> PlannerEntry:
    data = dict(meal_id=meal.id, user_id=user.id, position=0)
    data.update(overrides)
    entry = PlannerEntry(**data)
    db_session.add(entry)
    db_session.flush()
    return entry


def _row_for(response, user_id: int):
    return next(u for u in response.users if u.user_id == user_id)


# ---------------------------------------------------------------------------
# Last-active stamping
# ---------------------------------------------------------------------------

class TestTouchLastActive:
    def test_first_request_stamps(self, db_session: Session):
        user = _make_user(db_session)

        UserService(db_session).touch_last_active(user, now=NOW)

        db_session.refresh(user)
        assert user.last_active_at.replace(tzinfo=timezone.utc) == NOW

    def test_within_resolution_is_skipped(self, db_session: Session):
        user = _make_user(db_session, last_active_at=NOW)
        service = UserService(db_session)

        with patch.object(service.repo, "set_last_active") as set_last_active:
            service.touch_last_active(user, now=NOW + LAST_ACTIVE_RESOLUTION - timedelta(seconds=1))

        set_last_active.assert_not_called()

    def test_after_resolution_restamps(self, db_session: Session):
        user = _make_user(db_session, last_active_at=NOW)
        later = NOW + LAST_ACTIVE_RESOLUTION

        UserService(db_session).touch_last_active(user, now=later)

        db_session.refresh(user)
        assert user.last_active_at.replace(tzinfo=timezone.utc) == later

    def test_naive_stored_timestamp_is_treated_as_utc(self, db_session: Session):
        user = _make_user(db_session)
        user.last_active_at = NOW.replace(tzinfo=None)
        service = UserService(db_session)

        with patch.object(service.repo, "set_last_active") as set_last_active:
            service.touch_last_active(user, now=NOW + timedelta(minutes=1))

        set_last_active.assert_not_called()

    def test_does_not_bump_updated_at(self, db_session: Session):
        stamp = NOW - timedelta(days=3)
        user = _make_user(db_session, updated_at=stamp)

        UserService(db_session).touch_last_active(user, now=NOW)

        db_session.refresh(user)
        assert user.updated_at.replace(tzinfo=timezone.utc) == stamp


# ---------------------------------------------------------------------------
# Service: activity aggregation
# ---------------------------------------------------------------------------

class TestActivityCounts:
    def test_user_without_data_gets_zeros(self, db_session: Session):
        user = _make_user(db_session)

        row = _row_for(AdminService(db_session, user.id).get_activity_by_user(now=NOW), user.id)

        assert row.recipes == 0
        assert row.saved_meals == 0
        assert row.meals_cooked == 0
        assert row.shopping_items == 0
        assert row.last_active_at is None
        assert row.last_cooked_at is None

    def test_recipe_breakdown_excludes_starter_pack(self, db_session: Session):
        user = _make_user(db_session)
        _make_recipe(db_session, user)
        _make_recipe(db_session, user, is_ai_generated=True, created_at=NOW - timedelta(days=2))
        _make_recipe(db_session, user, source_url="https://example.com/r")
        _make_recipe(db_session, user, is_sample=True, is_favorite=True)

        row = _row_for(AdminService(db_session, user.id).get_activity_by_user(now=NOW), user.id)

        assert row.recipes == 3
        assert row.recipes_ai_generated == 1
        assert row.recipes_imported == 1
        assert row.recipes_recent == 1
        # Favoriting a starter recipe still counts as the user acting
        assert row.favorites == 1

    def test_planner_and_cooking_counts(self, db_session: Session):
        user = _make_user(db_session)
        recipe = _make_recipe(db_session, user)
        meal = _make_meal(db_session, user, recipe)
        _make_meal(db_session, user, recipe, is_saved=False)
        _make_meal(db_session, user, recipe, is_sample=True)
        _make_entry(db_session, user, meal)
        recent = NOW - timedelta(days=1)
        old = NOW - timedelta(days=90)
        _make_entry(db_session, user, meal, is_completed=True, completed_at=recent)
        _make_entry(db_session, user, meal, is_completed=True, completed_at=old, is_cleared=True)

        row = _row_for(AdminService(db_session, user.id).get_activity_by_user(now=NOW), user.id)

        assert row.saved_meals == 1
        assert row.planned_meals == 1
        assert row.meals_cooked == 2
        assert row.meals_cooked_recent == 1
        assert row.last_cooked_at == recent

    def test_collections_and_shopping(self, db_session: Session):
        user = _make_user(db_session)
        db_session.add(RecipeGroup(name="Weeknights", user_id=user.id))
        db_session.add_all(
            ShoppingItem(ingredient_name=name, user_id=user.id, aggregation_key=f"{name}::count")
            for name in ("eggs", "milk")
        )
        db_session.flush()

        row = _row_for(AdminService(db_session, user.id).get_activity_by_user(now=NOW), user.id)

        assert row.collections == 1
        assert row.shopping_items == 2

    def test_counts_are_isolated_per_user(self, db_session: Session):
        owner = _make_user(db_session)
        other = _make_user(db_session)
        _make_recipe(db_session, owner)

        response = AdminService(db_session, owner.id).get_activity_by_user(now=NOW)

        assert _row_for(response, owner.id).recipes == 1
        assert _row_for(response, other.id).recipes == 0


class TestActivitySummary:
    def test_summary_windows(self, db_session: Session):
        baseline = AdminService(db_session, 0).get_activity_by_user(now=NOW).summary

        _make_user(db_session, last_active_at=NOW - timedelta(days=2), created_at=NOW - timedelta(days=5))
        _make_user(db_session, last_active_at=NOW - timedelta(days=20), created_at=NOW - timedelta(days=200))
        _make_user(db_session, last_active_at=NOW - timedelta(days=45), created_at=NOW - timedelta(days=200))

        summary = AdminService(db_session, 0).get_activity_by_user(now=NOW).summary

        assert summary.total_users - baseline.total_users == 3
        assert summary.active_7d - baseline.active_7d == 1
        assert summary.active_30d - baseline.active_30d == 2
        assert summary.new_users_30d - baseline.new_users_30d == 1


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

def _admin_app() -> FastAPI:
    admin = MagicMock(spec=User)
    admin.id = 1
    admin.is_admin = True
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/admin")
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[require_admin] = lambda: admin
    return app


class TestActivityEndpoint:
    @patch("app.api.admin.AdminService")
    def test_returns_service_payload(self, mock_service_cls):
        mock_service_cls.return_value.get_activity_by_user.return_value = AdminActivityResponseDTO(
            window_days=30,
            summary=AdminActivitySummaryDTO(
                total_users=0, active_7d=0, active_30d=0, new_users_30d=0,
                recipes_recent=0, meals_cooked_recent=0,
            ),
            users=[],
        )

        response = TestClient(_admin_app()).get("/api/admin/activity")

        assert response.status_code == 200
        assert response.json()["window_days"] == 30
