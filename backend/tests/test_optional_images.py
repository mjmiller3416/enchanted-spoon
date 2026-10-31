"""Real database reservations with mocked providers: no paid API calls."""
from unittest.mock import AsyncMock, patch
import pytest
from app.services.ai.optional_images import generate_optional_recipe_images
from app.services.usage_service import UsageService
from app.models.user import User

@pytest.fixture
def anyio_backend():
    return "asyncio"



@pytest.fixture
def photo_account(file_db):
    with file_db() as session:
        yield session, session.get(User, 1)


@pytest.mark.anyio
async def test_reserves_before_provider_and_blocks_next_free_photo(photo_account):
    db_session, test_user = photo_account
    test_user.is_admin = False
    test_user.subscription_tier = "free"
    usage = UsageService(db_session, test_user.id)
    async def generate(name):
        assert usage.get_usage().ai_images_generated == 1
        return {"reference_image_data": "ref", "banner_image_data": "banner"}
    with patch("app.services.ai.optional_images.get_image_generation_service") as factory:
        provider = factory.return_value.generate_dual_recipe_images = AsyncMock(side_effect=generate)
        assert await generate_optional_recipe_images(db_session, test_user, "Soup") == ("ref", "banner")
        assert await generate_optional_recipe_images(db_session, test_user, "Soup") == (None, None)
        assert provider.await_count == 1
        assert usage.get_usage().ai_images_generated == 1


@pytest.mark.anyio
@pytest.mark.parametrize("outcome", [{"success": False}, RuntimeError("provider failure")])
async def test_full_failure_refunds(photo_account, outcome):
    db_session, test_user = photo_account
    with patch("app.services.ai.optional_images.get_image_generation_service") as factory:
        provider = AsyncMock()
        if isinstance(outcome, Exception):
            provider.side_effect = outcome
        else:
            provider.return_value = outcome
        factory.return_value.generate_dual_recipe_images = provider
        assert await generate_optional_recipe_images(db_session, test_user, "Soup") == (None, None)
        assert UsageService(db_session, test_user.id).get_usage().ai_images_generated == 0


@pytest.mark.anyio
async def test_partial_success_consumes_one_unit(photo_account):
    db_session, test_user = photo_account
    with patch("app.services.ai.optional_images.get_image_generation_service") as factory:
        factory.return_value.generate_dual_recipe_images = AsyncMock(return_value={"banner_image_data": "banner"})
        assert await generate_optional_recipe_images(db_session, test_user, "Soup") == (None, "banner")
        assert UsageService(db_session, test_user.id).get_usage().ai_images_generated == 1


@pytest.mark.anyio
async def test_reservation_error_never_calls_provider(photo_account):
    db_session, test_user = photo_account
    with patch("app.services.ai.optional_images.UsageService.reserve", side_effect=RuntimeError), patch("app.services.ai.optional_images.get_image_generation_service") as factory:
        assert await generate_optional_recipe_images(db_session, test_user, "Soup") == (None, None)
        factory.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize("partial_success", [False, True])
async def test_provider_failure_preserves_recipe_and_accounts_for_images(photo_account, partial_success):
    """Exercise real recipe/image orchestration and sanitization with a mocked SDK."""
    import json
    from unittest.mock import MagicMock
    from google.genai.errors import ClientError
    from app.dtos.recipe_generation_dtos import RecipeGenerationRequestDTO
    from app.services.ai.image_generation.service import ImageGenerationService
    from app.services.ai.recipe_generation.service import RecipeGenerationService
    from app.services.ai.provider_errors import AI_UNAVAILABLE_MESSAGE

    session, user = photo_account
    user.is_admin = False
    user.usage_plan = "launch"
    user.subscription_tier = "free"
    session.commit()
    usage = UsageService(session, user.id)
    error = ClientError(402, {"error": {"code": 402, "message": "synthetic-private-provider-detail"}})
    image_client = MagicMock()
    calls = 0

    async def provider_call(**kwargs):
        nonlocal calls
        calls += 1
        assert usage.get_usage().ai_images_generated == 1
        if partial_success and calls == 1:
            return MagicMock()
        raise error

    image_client.aio.models.generate_content = AsyncMock(side_effect=provider_call)
    image_service = ImageGenerationService.__new__(ImageGenerationService)
    recipe_service = RecipeGenerationService.__new__(RecipeGenerationService)
    captured = []
    original = image_service.generate_dual_recipe_images

    async def images(name):
        result = await original(name)
        captured.append(result)
        return result

    recipe_json = json.dumps({"recipe_name": "Soup", "ingredients": [
        {"ingredient_name": "Salt", "ingredient_category": "pantry"}], "directions": "Simmer."})
    with patch("app.services.ai.image_generation.service.get_gemini_client", return_value=image_client), \
         patch("app.services.ai.image_generation.service.extract_image_data", return_value="aW1hZ2U="), \
         patch("app.services.ai.optional_images.get_image_generation_service", return_value=image_service), \
         patch.object(image_service, "generate_dual_recipe_images", side_effect=images), \
         patch("app.services.ai.recipe_generation.service.get_gemini_client", return_value=MagicMock()), \
         patch("app.services.ai.recipe_generation.service.extract_text_from_response", return_value=recipe_json):
        async def metered_images(name):
            return await generate_optional_recipe_images(session, user, name)
        result = await recipe_service.generate(
            RecipeGenerationRequestDTO(prompt="Make soup", generate_image=True, estimate_nutrition=False),
            image_generator=metered_images,
        )

    assert result.success is True
    assert result.recipe.recipe_name == "Soup"
    assert result.banner_image_data is None
    assert bool(result.reference_image_data) == partial_success
    assert usage.get_usage().ai_images_generated == int(partial_success)
    assert calls == 2
    assert all(AI_UNAVAILABLE_MESSAGE in message for message in captured[0]["errors"])
    assert "synthetic-private-provider-detail" not in str(captured)
