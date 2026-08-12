"""Tests for the nutrition estimation API endpoint.

Covers:
- POST /api/ai/nutrition-estimation — success path
- POST /api/ai/nutrition-estimation — error from service
- Auth: requires pro access
- Request validation
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ai.nutrition_estimation import router
from app.dtos.nutrition_dtos import (
    NutritionEstimationResponseDTO,
    NutritionFactsDTO,
)
from app.models.user import User


# ---------------------------------------------------------------------------
# App and client setup
# ---------------------------------------------------------------------------

def _create_test_app(user: User | None = None) -> FastAPI:
    """Build a minimal FastAPI app with the nutrition router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/api/ai/nutrition-estimation")

    # Override auth dependency. AI routes gate on require_within_usage_limit,
    # which resolves the user via get_current_user — the binary require_pro
    # gate was dropped when the metered free tier landed (#164).
    from app.api.auth import get_current_user
    from app.database.db import get_session

    # Mock session
    mock_session = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_session

    if user:
        app.dependency_overrides[get_current_user] = lambda: user

    return app


def _make_pro_user() -> User:
    """Create a User object with pro access."""
    user = MagicMock(spec=User)
    user.id = 1
    user.has_pro_access = True
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNutritionEstimationEndpoint:
    """Tests for POST /api/ai/nutrition-estimation."""

    @patch("app.api.ai.nutrition_estimation.get_nutrition_estimation_service")
    @patch("app.api.ai.nutrition_estimation.UsageService")
    def test_successful_estimation(self, mock_usage_cls, mock_get_service):
        """Successful estimation returns 200 with nutrition data."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.estimate.return_value = NutritionEstimationResponseDTO(
            success=True,
            nutrition_facts=NutritionFactsDTO(
                calories=350,
                protein_g=12.5,
                is_ai_estimated=True,
            ),
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={
                "recipe_name": "Pancakes",
                "ingredients": [
                    {"ingredient_name": "Flour", "quantity": 2.0, "unit": "cups"},
                    {"ingredient_name": "Eggs", "quantity": 2.0},
                ],
                "servings": 4,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["nutrition_facts"]["calories"] == 350
        assert data["nutrition_facts"]["is_ai_estimated"] is True

    @patch("app.api.ai.nutrition_estimation.get_nutrition_estimation_service")
    @patch("app.api.ai.nutrition_estimation.UsageService")
    def test_service_returns_error(self, mock_usage_cls, mock_get_service):
        """Service returning success=False raises 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.estimate.return_value = NutritionEstimationResponseDTO(
            success=False,
            error="Could not parse AI response",
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={
                "recipe_name": "Test",
                "ingredients": [{"ingredient_name": "Something"}],
            },
        )

        assert response.status_code == 500

    @patch("app.api.ai.nutrition_estimation.get_nutrition_estimation_service")
    @patch("app.api.ai.nutrition_estimation.UsageService")
    def test_service_raises_exception(self, mock_usage_cls, mock_get_service):
        """Unhandled exception in the service returns 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.estimate.side_effect = RuntimeError("Unexpected error")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={
                "recipe_name": "Test",
                "ingredients": [{"ingredient_name": "Something"}],
            },
        )

        assert response.status_code == 500
        assert "Nutrition estimation failed" in response.json()["detail"]

    def test_missing_recipe_name_returns_422(self):
        """Missing required field recipe_name returns 422 validation error."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={
                "ingredients": [{"ingredient_name": "Flour"}],
            },
        )

        assert response.status_code == 422

    def test_missing_ingredients_returns_422(self):
        """Missing required field ingredients returns 422."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={"recipe_name": "Test"},
        )

        assert response.status_code == 422

    def test_invalid_servings_returns_422(self):
        """Servings < 1 returns 422."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={
                "recipe_name": "Test",
                "ingredients": [{"ingredient_name": "Flour"}],
                "servings": 0,
            },
        )

        assert response.status_code == 422

    @patch("app.api.ai.nutrition_estimation.get_nutrition_estimation_service")
    @patch("app.api.ai.nutrition_estimation.UsageService")
    def test_usage_tracking_failure_is_silent(self, mock_usage_cls, mock_get_service):
        """Usage tracking failure doesn't break the response."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.estimate.return_value = NutritionEstimationResponseDTO(
            success=True,
            nutrition_facts=NutritionFactsDTO(calories=100),
        )
        mock_get_service.return_value = mock_service

        # Make usage tracking throw
        mock_usage_instance = MagicMock()
        mock_usage_instance.increment.side_effect = RuntimeError("DB error")
        mock_usage_cls.return_value = mock_usage_instance

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={
                "recipe_name": "Test",
                "ingredients": [{"ingredient_name": "Flour"}],
            },
        )

        # Should still succeed
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_no_auth_returns_401(self):
        """An unauthenticated request is rejected before the AI service runs.

        AI routes no longer gate on pro access (metered free tier, #164) — they
        require authentication via get_current_user and meter usage per tier.
        A failed auth dependency surfaces as the route's error.
        """
        from fastapi import HTTPException

        from app.api.auth import get_current_user
        from app.database.db import get_session

        app = FastAPI()
        app.include_router(router, prefix="/api/ai/nutrition-estimation")

        def deny_access():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = deny_access
        app.dependency_overrides[get_session] = lambda: MagicMock()

        client = TestClient(app)

        response = client.post(
            "/api/ai/nutrition-estimation",
            json={
                "recipe_name": "Test",
                "ingredients": [{"ingredient_name": "Flour"}],
            },
        )

        assert response.status_code == 401
