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
