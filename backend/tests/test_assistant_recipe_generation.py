"""Tests for the assistant chat's create_recipe tool.

Regression coverage for #135: when the shared recipe-generation service
failed or returned a hollow result (no ingredients), the assistant used to
swallow the failure and hand back a fake "successful" recipe with an empty
ingredient list and no directions. It should instead report the failure so
the caller can tell the user, matching how the standalone generation
endpoint surfaces failures.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.dtos.recipe_generation_dtos import (
    GeneratedIngredientDTO,
    RecipeGeneratedDTO,
    RecipeGenerationResponseDTO,
)
from app.services.ai.assistant import AssistantService


def _make_service() -> AssistantService:
    """Build a service instance without running __init__ (skips client setup)."""
    return AssistantService.__new__(AssistantService)


def _full_recipe() -> RecipeGeneratedDTO:
    return RecipeGeneratedDTO(
        recipe_name="Tacos",
        recipe_category="other",
        meal_type="dinner",
        directions="1. Cook.\n2. Eat.",
        ingredients=[
            GeneratedIngredientDTO(ingredient_name="Tortillas", ingredient_category="bakery"),
        ],
    )


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class TestGenerateRecipeFromArgs:
    async def test_successful_generation_returns_recipe(self):
        service = _make_service()
        recipe = _full_recipe()
        with patch(
            "app.services.ai.assistant.generators.get_recipe_generation_service"
        ) as get_service:
            get_service.return_value.generate = AsyncMock(
                return_value=RecipeGenerationResponseDTO(success=True, recipe=recipe)
            )
            result = await service._generate_recipe_from_args({"recipe_name": "Tacos"})

        assert result is recipe

    async def test_service_exception_returns_none(self):
        service = _make_service()
        with patch(
            "app.services.ai.assistant.generators.get_recipe_generation_service"
        ) as get_service:
            get_service.return_value.generate = AsyncMock(side_effect=RuntimeError("boom"))
            result = await service._generate_recipe_from_args({"recipe_name": "Tacos"})

        assert result is None

    async def test_transient_parse_error_is_retried(self):
        """A single malformed/truncated AI response (issue #177) should not sink
        the whole request — the service should retry before giving up."""
        from app.services.ai.recipe_generation.service import RecipeParseError

        service = _make_service()
        recipe = _full_recipe()
        with patch(
            "app.services.ai.assistant.generators.get_recipe_generation_service"
        ) as get_service:
            get_service.return_value.generate = AsyncMock(
                side_effect=[
                    RecipeParseError("truncated JSON"),
                    RecipeGenerationResponseDTO(success=True, recipe=recipe),
                ]
            )
            result = await service._generate_recipe_from_args({"recipe_name": "Tacos"})

        assert result is recipe
        assert get_service.return_value.generate.await_count == 2

    async def test_hollow_success_returns_none(self):
        """success=True but no ingredients must not be treated as a real recipe."""
        service = _make_service()
        hollow = RecipeGeneratedDTO(recipe_name="Tacos", ingredients=[])
        with patch(
            "app.services.ai.assistant.generators.get_recipe_generation_service"
        ) as get_service:
            get_service.return_value.generate = AsyncMock(
                return_value=RecipeGenerationResponseDTO(success=True, recipe=hollow)
            )
            result = await service._generate_recipe_from_args({"recipe_name": "Tacos"})

        assert result is None


class TestHandleFunctionCallCreateRecipe:
    async def test_successful_recipe_returned_as_recipe_type(self):
        service = _make_service()
        recipe = _full_recipe()
        service._generate_recipe_from_args = AsyncMock(return_value=recipe)

        result = await service._handle_function_call(
            "create_recipe", {"recipe_name": "Tacos"}, None, contents=[]
        )

        assert result["type"] == "recipe"
        assert result["recipe"] is recipe

    async def test_failed_generation_returns_chat_message_not_fake_recipe(self):
        service = _make_service()
        service._generate_recipe_from_args = AsyncMock(return_value=None)

        result = await service._handle_function_call(
            "create_recipe", {"recipe_name": "Tacos"}, None, contents=[]
        )

        assert result["type"] == "chat"
        assert result.get("recipe") is None
        assert result["response"]
