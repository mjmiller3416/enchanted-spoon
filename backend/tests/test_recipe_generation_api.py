"""Tests for the recipe generation API endpoint.

Covers:
- POST /api/ai/wizard-generation — success path
- POST /api/ai/wizard-generation — RecipeGenerationError from service
- POST /api/ai/wizard-generation — RecipeParseError from service
- POST /api/ai/wizard-generation — service returns success=False
- Auth: requires pro access
- Request validation (missing prompt, prompt too long, invalid servings)
- Usage tracking silent failure
- User category injection
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ai.recipe_generation import router
from app.dtos.recipe_generation_dtos import (
    GeneratedIngredientDTO,
    RecipeGeneratedDTO,
    RecipeGenerationResponseDTO,
)
from app.dtos.nutrition_dtos import NutritionFactsDTO
from app.models.user import User
from app.services.ai.recipe_generation.service import (
    RecipeGenerationError,
    RecipeParseError,
)


# ---------------------------------------------------------------------------
# App and client setup
# ---------------------------------------------------------------------------

def _create_test_app(user: User | None = None) -> FastAPI:
    """Build a minimal FastAPI app with the recipe generation router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/api/ai/wizard-generation")

    from app.api.auth import require_pro
    from app.database.db import get_session

    mock_session = MagicMock()
    # No existing UserUsage row - the usage-limit dependency creates a fresh
    # (zeroed) one, which is always under cap.
    mock_session.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session

    if user:
        app.dependency_overrides[require_pro] = lambda: user

    return app


def _make_pro_user() -> User:
    """Create a User object with pro access."""
    user = MagicMock(spec=User)
    user.id = 1
    user.is_admin = False
    user.has_pro_access = True
    return user


def _make_success_response() -> RecipeGenerationResponseDTO:
    """Create a successful generation response for mocking."""
    return RecipeGenerationResponseDTO(
        success=True,
        recipe=RecipeGeneratedDTO(
            recipe_name="Spicy Thai Green Curry",
            recipe_category="vegetarian",
            meal_type="dinner",
            diet_pref="vegetarian",
            description="A fragrant Thai green curry.",
            prep_time=15,
            cook_time=25,
            difficulty="Medium",
            servings=4,
            ingredients=[
                GeneratedIngredientDTO(
                    ingredient_name="Coconut Milk",
                    ingredient_category="pantry",
                    quantity=1.0,
                    unit="can",
                ),
            ],
            directions="Heat oil.\nAdd paste.\nSimmer.",
            notes="Serve with rice.",
        ),
        nutrition_facts=NutritionFactsDTO(
            calories=450,
            protein_g=12.5,
            is_ai_estimated=True,
        ),
    )


def _valid_request_body() -> dict:
    """Return a valid JSON request body for the recipe generation endpoint."""
    return {
        "prompt": "A spicy Thai green curry for 4",
        "preferences": {
            "category": "thai",
            "dietary": "Vegetarian",
            "difficulty": "Medium",
            "servings": 4,
            "meal_type": "dinner",
        },
        "generate_image": False,
        "estimate_nutrition": True,
    }


# ---------------------------------------------------------------------------
# Tests — success
# ---------------------------------------------------------------------------

class TestRecipeGenerationEndpoint:
    """Tests for POST /api/ai/wizard-generation."""

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_successful_generation(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """Successful generation returns 200 with recipe data."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.return_value = _make_success_response()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["recipe"]["recipe_name"] == "Spicy Thai Green Curry"
        assert data["recipe"]["prep_time"] == 15
        assert data["recipe"]["difficulty"] == "Medium"
        assert len(data["recipe"]["ingredients"]) == 1
        assert data["nutrition_facts"]["calories"] == 450
        assert data["nutrition_facts"]["is_ai_estimated"] is True

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_minimal_request(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """Request with only prompt (no preferences) returns 200."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.return_value = _make_success_response()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json={"prompt": "Simple pasta recipe"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_user_categories_injected(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """User's enabled categories are injected into the request."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        # Mock category service to return user categories
        mock_cat_instance = MagicMock()
        mock_cat_instance.get_all_categories.return_value = [
            MagicMock(value="italian"),
            MagicMock(value="mexican"),
            MagicMock(value="thai"),
        ]
        mock_cat_cls.return_value = mock_cat_instance

        mock_service = MagicMock()
        mock_service.generate.return_value = _make_success_response()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json={"prompt": "A pasta dish"},
        )

        assert response.status_code == 200
        # Verify the service was called with categories injected
        call_args = mock_service.generate.call_args[0][0]
        assert call_args.allowed_categories == ["italian", "mexican", "thai"]


# ---------------------------------------------------------------------------
# Tests — error handling
# ---------------------------------------------------------------------------

class TestRecipeGenerationErrors:
    """Tests for error responses."""

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_service_returns_failure(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """Service returning success=False raises 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.return_value = RecipeGenerationResponseDTO(
            success=False,
            error="Model returned empty response",
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_recipe_generation_error(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """RecipeGenerationError from service returns 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.side_effect = RecipeGenerationError("API quota exceeded")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500
        assert "Recipe generation failed" in response.json()["detail"]

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_recipe_parse_error(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """RecipeParseError from service returns 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.side_effect = RecipeParseError("Malformed JSON from AI")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500
        assert "parse" in response.json()["detail"].lower()

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_unexpected_exception(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """Unhandled exception returns 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.side_effect = RuntimeError("Unexpected failure")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500
        assert "Recipe generation failed" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Tests — request validation
# ---------------------------------------------------------------------------

class TestRecipeGenerationValidation:
    """Tests for request body validation."""

    def test_missing_prompt_returns_422(self):
        """Missing required 'prompt' field returns 422."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        response = client.post(
            "/api/ai/wizard-generation",
            json={"generate_image": True},
        )

        assert response.status_code == 422

    def test_empty_prompt_returns_422(self):
        """Empty prompt string returns 422 (min_length=1)."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        response = client.post(
            "/api/ai/wizard-generation",
            json={"prompt": ""},
        )

        assert response.status_code == 422

    def test_prompt_too_long_returns_422(self):
        """Prompt exceeding 500 chars returns 422."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        response = client.post(
            "/api/ai/wizard-generation",
            json={"prompt": "x" * 501},
        )

        assert response.status_code == 422

    def test_invalid_servings_preference_returns_422(self):
        """Servings < 1 in preferences returns 422."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        response = client.post(
            "/api/ai/wizard-generation",
            json={
                "prompt": "Some recipe",
                "preferences": {"servings": 0},
            },
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — auth
# ---------------------------------------------------------------------------

class TestRecipeGenerationAuth:
    """Tests for authentication requirements."""

    def test_no_auth_returns_403(self):
        """Request without pro access returns 403."""
        from fastapi import HTTPException

        from app.api.auth import require_pro
        from app.database.db import get_session

        app = FastAPI()
        app.include_router(router, prefix="/api/ai/wizard-generation")

        def deny_access():
            raise HTTPException(status_code=403, detail="Pro subscription required")

        app.dependency_overrides[require_pro] = deny_access
        app.dependency_overrides[get_session] = lambda: MagicMock()

        client = TestClient(app)

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Tests — usage tracking
# ---------------------------------------------------------------------------

class TestRecipeGenerationUsageTracking:
    """Tests for usage tracking behavior."""

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_usage_tracking_failure_is_silent(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """Usage tracking failure doesn't break the response."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.return_value = _make_success_response()
        mock_get_service.return_value = mock_service

        mock_usage_instance = MagicMock()
        mock_usage_instance.increment.side_effect = RuntimeError("DB error")
        mock_usage_cls.return_value = mock_usage_instance

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    @patch("app.api.ai.recipe_generation.UsageService")
    def test_usage_tracked_on_success(self, mock_usage_cls, mock_get_service, mock_cat_cls):
        """Usage is incremented on successful generation."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate.return_value = _make_success_response()
        mock_get_service.return_value = mock_service

        mock_usage_instance = MagicMock()
        mock_usage_cls.return_value = mock_usage_instance

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 200
        mock_usage_instance.increment.assert_called_once_with("ai_suggestions_requested")


# ---------------------------------------------------------------------------
# Tests — monthly usage limit enforcement
# ---------------------------------------------------------------------------

class TestRecipeGenerationUsageLimit:
    """Tests for require_within_usage_limit gating this endpoint."""

    def test_over_cap_returns_429(self):
        """A user at their monthly cap gets 429 before the AI service runs."""
        from app.api.auth import require_pro
        from app.models.user_usage import UserUsage

        user = _make_pro_user()
        app = FastAPI()
        app.include_router(router, prefix="/api/ai/wizard-generation")

        maxed_usage = UserUsage(user_id=user.id, month="2026-08")
        maxed_usage.ai_suggestions_requested = 300  # at the "pro" tier cap

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = maxed_usage
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[require_pro] = lambda: user

        client = TestClient(app)
        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 429
        assert response.json()["detail"]["field"] == "ai_suggestions_requested"

    def test_admin_bypasses_cap(self):
        """Admins skip the usage-limit check entirely, even over cap."""
        from app.api.auth import require_pro
        from app.models.user_usage import UserUsage

        admin = MagicMock(spec=User)
        admin.id = 2
        admin.is_admin = True
        admin.has_pro_access = True

        app = FastAPI()
        app.include_router(router, prefix="/api/ai/wizard-generation")

        maxed_usage = UserUsage(user_id=admin.id, month="2026-08")
        maxed_usage.ai_suggestions_requested = 999999

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = maxed_usage
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[require_pro] = lambda: admin

        with patch("app.api.ai.recipe_generation.UserCategoryService"), \
                patch("app.api.ai.recipe_generation.get_recipe_generation_service") as mock_get_service, \
                patch("app.api.ai.recipe_generation.UsageService"):
            mock_service = MagicMock()
            mock_service.generate.return_value = _make_success_response()
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            response = client.post(
                "/api/ai/wizard-generation",
                json=_valid_request_body(),
            )

        assert response.status_code == 200

    def test_under_cap_proceeds(self):
        """A user under their monthly cap is allowed through to the AI service."""
        from app.api.auth import require_pro
        from app.models.user_usage import UserUsage

        user = _make_pro_user()
        app = FastAPI()
        app.include_router(router, prefix="/api/ai/wizard-generation")

        low_usage = UserUsage(user_id=user.id, month="2026-08")
        low_usage.ai_suggestions_requested = 1

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = low_usage
        app.dependency_overrides[get_session] = lambda: mock_session
        app.dependency_overrides[require_pro] = lambda: user

        with patch("app.api.ai.recipe_generation.UserCategoryService"), \
                patch("app.api.ai.recipe_generation.get_recipe_generation_service") as mock_get_service, \
                patch("app.api.ai.recipe_generation.UsageService"):
            mock_service = MagicMock()
            mock_service.generate.return_value = _make_success_response()
            mock_get_service.return_value = mock_service

            client = TestClient(app)
            response = client.post(
                "/api/ai/wizard-generation",
                json=_valid_request_body(),
            )

        assert response.status_code == 200
