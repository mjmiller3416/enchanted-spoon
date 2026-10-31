"""Tests for the recipe generation API endpoint.

Covers:
- POST /api/ai/wizard-generation â€” success path
- POST /api/ai/wizard-generation â€” RecipeGenerationError from service
- POST /api/ai/wizard-generation â€” RecipeParseError from service
- POST /api/ai/wizard-generation â€” service returns success=False
- Auth: requires pro access
- Request validation (missing prompt, prompt too long, invalid servings)
- Usage reservation: counted once on success, refunded on failure, 429 at cap
- User category injection
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ai.recipe_generation import router
from app.core.usage_limits import TIER_USAGE_LIMITS

PRO_SUGGESTION_CAP = TIER_USAGE_LIMITS["pro"]["ai_suggestions_requested"]
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

    # AI routes gate on require_within_usage_limit, which resolves the user via
    # get_current_user â€” the binary require_pro gate was dropped when the
    # metered free tier landed (#164).
    from app.api.auth import get_current_user
    from app.database.db import get_session

    mock_session = MagicMock()
    # No existing UserUsage row - the usage-limit dependency creates a fresh
    # (zeroed) one, which is always under cap.
    mock_session.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_session] = lambda: mock_session

    if user:
        app.dependency_overrides[get_current_user] = lambda: user

    return app


def _make_pro_user() -> User:
    """Create a User object with pro access."""
    user = MagicMock(spec=User)
    user.id = 1
    user.usage_plan = "launch"
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
# Tests â€” success
# ---------------------------------------------------------------------------

class TestRecipeGenerationEndpoint:
    """Tests for POST /api/ai/wizard-generation."""

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_successful_generation(self, mock_get_service, mock_cat_cls):
        """Successful generation returns 200 with recipe data."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate = AsyncMock(return_value=_make_success_response())
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
    def test_minimal_request(self, mock_get_service, mock_cat_cls):
        """Request with only prompt (no preferences) returns 200."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate = AsyncMock(return_value=_make_success_response())
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json={"prompt": "Simple pasta recipe"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_user_categories_injected(self, mock_get_service, mock_cat_cls):
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
        mock_service.generate = AsyncMock(return_value=_make_success_response())
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
# Tests â€” error handling
# ---------------------------------------------------------------------------

class TestRecipeGenerationErrors:
    """Tests for error responses."""

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_service_returns_failure(self, mock_get_service, mock_cat_cls):
        """Service returning success=False raises 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate = AsyncMock(
            return_value=RecipeGenerationResponseDTO(
                success=False,
                error="Model returned empty response",
            )
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_recipe_generation_error(self, mock_get_service, mock_cat_cls):
        """RecipeGenerationError from service returns 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate = AsyncMock(
            side_effect=RecipeGenerationError("API quota exceeded")
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500
        assert "Recipe generation failed" in response.json()["detail"]

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_recipe_parse_error(self, mock_get_service, mock_cat_cls):
        """RecipeParseError from service returns 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate = AsyncMock(
            side_effect=RecipeParseError("Malformed JSON from AI")
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500
        assert "parse" in response.json()["detail"].lower()

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_unexpected_exception(self, mock_get_service, mock_cat_cls):
        """Unhandled exception returns 500."""
        user = _make_pro_user()
        app = _create_test_app(user)
        client = TestClient(app)

        mock_service = MagicMock()
        mock_service.generate = AsyncMock(side_effect=RuntimeError("Unexpected failure"))
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 500
        assert "Recipe generation failed" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Tests â€” request validation
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
# Tests â€” auth
# ---------------------------------------------------------------------------

class TestRecipeGenerationAuth:
    """Tests for authentication requirements."""

    def test_no_auth_returns_401(self):
        """An unauthenticated request is rejected before the AI service runs.

        AI routes no longer gate on pro access (metered free tier, #164) â€” they
        require authentication via get_current_user and meter usage per tier.
        """
        from fastapi import HTTPException

        from app.api.auth import get_current_user
        from app.database.db import get_session

        app = FastAPI()
        app.include_router(router, prefix="/api/ai/wizard-generation")

        def deny_access():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = deny_access
        app.dependency_overrides[get_session] = lambda: MagicMock()

        client = TestClient(app)

        response = client.post(
            "/api/ai/wizard-generation",
            json=_valid_request_body(),
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests â€” usage tracking and monthly limit enforcement (real database)
# ---------------------------------------------------------------------------

def _usage_app(file_db, user) -> FastAPI:
    """Mount the router against a real DB so reservations actually persist."""
    from app.api.auth import get_current_user
    from app.database.db import get_session

    app = FastAPI()
    app.include_router(router, prefix="/api/ai/wizard-generation")

    def _session():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def _seed_usage(file_db, count: int) -> None:
    from app.models.user_usage import UserUsage

    with file_db() as session:
        session.add(UserUsage(
            user_id=1,
            month=UserUsage.get_current_month(),
            ai_suggestions_requested=count,
        ))
        session.commit()


def _suggestions_used(file_db) -> int:
    from app.models.user_usage import UserUsage

    with file_db() as session:
        usage = session.query(UserUsage).filter_by(user_id=1).first()
        return usage.ai_suggestions_requested if usage else 0


class TestRecipeGenerationUsage:
    """require_within_usage_limit reserves before the call, refunds on failure."""

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_usage_counted_once_on_success(self, mock_get_service, mock_cat_cls, file_db):
        mock_service = MagicMock()
        mock_service.generate = AsyncMock(return_value=_make_success_response())
        mock_get_service.return_value = mock_service

        client = TestClient(_usage_app(file_db, _make_pro_user()))
        response = client.post("/api/ai/wizard-generation", json=_valid_request_body())

        assert response.status_code == 200
        assert _suggestions_used(file_db) == 1

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_failed_generation_is_refunded(self, mock_get_service, mock_cat_cls, file_db):
        mock_service = MagicMock()
        mock_service.generate = AsyncMock(side_effect=RecipeGenerationError("boom"))
        mock_get_service.return_value = mock_service
        _seed_usage(file_db, 4)

        client = TestClient(_usage_app(file_db, _make_pro_user()))
        response = client.post("/api/ai/wizard-generation", json=_valid_request_body())

        assert response.status_code == 500
        assert _suggestions_used(file_db) == 4

    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_over_cap_returns_429(self, mock_get_service, file_db):
        """A user at their monthly cap gets 429 before the AI service runs."""
        _seed_usage(file_db, PRO_SUGGESTION_CAP)  # at the "pro" tier cap

        client = TestClient(_usage_app(file_db, _make_pro_user()))
        response = client.post("/api/ai/wizard-generation", json=_valid_request_body())

        assert response.status_code == 429
        assert response.json()["detail"]["field"] == "ai_suggestions_requested"
        assert response.json()["detail"]["current"] == PRO_SUGGESTION_CAP
        mock_get_service.assert_not_called()
        assert _suggestions_used(file_db) == PRO_SUGGESTION_CAP

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_admin_bypasses_cap_but_is_counted(self, mock_get_service, mock_cat_cls, file_db):
        admin = MagicMock(spec=User)
        admin.id = 1
        admin.is_admin = True
        admin.has_pro_access = True
        mock_service = MagicMock()
        mock_service.generate = AsyncMock(return_value=_make_success_response())
        mock_get_service.return_value = mock_service
        _seed_usage(file_db, 999_999)

        client = TestClient(_usage_app(file_db, admin))
        response = client.post("/api/ai/wizard-generation", json=_valid_request_body())

        assert response.status_code == 200
        assert _suggestions_used(file_db) == 1_000_000

    @patch("app.api.ai.recipe_generation.UserCategoryService")
    @patch("app.api.ai.recipe_generation.get_recipe_generation_service")
    def test_last_unit_under_cap_proceeds(self, mock_get_service, mock_cat_cls, file_db):
        mock_service = MagicMock()
        mock_service.generate = AsyncMock(return_value=_make_success_response())
        mock_get_service.return_value = mock_service
        _seed_usage(file_db, PRO_SUGGESTION_CAP - 1)

        client = TestClient(_usage_app(file_db, _make_pro_user()))
        first = client.post("/api/ai/wizard-generation", json=_valid_request_body())
        second = client.post("/api/ai/wizard-generation", json=_valid_request_body())

        assert first.status_code == 200
        assert second.status_code == 429
        assert _suggestions_used(file_db) == PRO_SUGGESTION_CAP


@pytest.mark.parametrize("provider_status", [402, 503, None])
def test_wizard_provider_error_is_private_and_refunded(file_db, caplog, provider_status):
    """Real wizard service + route + quota dependency; only the SDK is mocked."""
    import logging
    import traceback
    from google.genai import errors
    from app.services.ai.recipe_generation.service import RecipeGenerationService

    sentinel = "synthetic-sensitive-wizard-provider-payload"
    if provider_status is None:
        class UnfamiliarProviderFailure(Exception):
            pass
        failure = UnfamiliarProviderFailure(sentinel)
    else:
        error_class = errors.ServerError if provider_status >= 500 else errors.ClientError
        failure = error_class(provider_status, {"error": {"code": provider_status, "message": sentinel}})
    sdk = MagicMock()
    sdk.models.generate_content.side_effect = failure
    service = RecipeGenerationService.__new__(RecipeGenerationService)
    _seed_usage(file_db, 4)
    client = TestClient(_usage_app(file_db, _make_pro_user()))
    loggers = [logging.getLogger(name) for name in ("app.services.ai.provider_errors", "app.api")]
    disabled = [logger.disabled for logger in loggers]
    for logger in loggers:
        logger.disabled = False
    try:
        with caplog.at_level(logging.ERROR), \
             patch("app.api.ai.recipe_generation.get_recipe_generation_service", return_value=service), \
             patch("app.api.ai.recipe_generation.UserCategoryService"), \
             patch("app.services.ai.recipe_generation.service.get_gemini_client", return_value=sdk):
            response = client.post("/api/ai/wizard-generation", json=_valid_request_body())
    finally:
        for logger, previous in zip(loggers, disabled):
            logger.disabled = previous

    assert response.status_code == 500
    assert sentinel not in response.text
    assert _suggestions_used(file_db) == 4
    assert sentinel not in caplog.text
    provider_records = [record for record in caplog.records if record.name == "app.services.ai.provider_errors"]
    assert provider_records
    assert f"status={provider_status}" in provider_records[-1].getMessage()
    if provider_status is None:
        assert "UnfamiliarProviderFailure" in provider_records[-1].getMessage()
    for record in caplog.records:
        assert sentinel not in repr(record.__dict__)
        if record.exc_info:
            assert sentinel not in "".join(traceback.format_exception(*record.exc_info))
            attached = record.exc_info[1]
            assert attached.__cause__ is None
            assert attached.__context__ is None
