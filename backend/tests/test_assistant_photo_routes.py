"""API-level regression coverage for automatic photos and optional quota exhaustion."""
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.ai.assistant import router
from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.recipe_generation_dtos import RecipeGeneratedDTO
from app.models.user import User
from app.models.user_usage import UserUsage


@pytest.mark.parametrize("path, generate_image, photo_count", [("/chat", False, 0), ("/generate-recipe", True, 1)])
def test_recipe_succeeds_without_unbudgeted_photos(file_db, path, generate_image, photo_count):
    app = FastAPI()
    app.include_router(router)
    with file_db() as session:
        user = session.get(User, 1)
        session.add(UserUsage(user_id=1, month=UserUsage.get_current_month(), ai_images_generated=photo_count))
        session.commit()
    def session_dependency():
        with file_db() as session:
            yield session
    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_current_user] = lambda: user
    with patch("app.api.ai.assistant.get_assistant_service") as service, patch("app.api.ai.assistant.UserContextBuilder") as context, patch("app.services.ai.optional_images.get_image_generation_service") as images:
        context.return_value.build_context_data.return_value = {}
        service.return_value.chat = AsyncMock(return_value={"type": "recipe", "recipe": RecipeGeneratedDTO(recipe_name="Soup"), "response": "Ready"})
        response = TestClient(app).post(path, json={"message": "Create soup", "generate_image": generate_image})
        assert response.status_code == 200
        assert response.json()["recipe"]["recipe_name"] == "Soup"
        assert response.json()["reference_image_data"] is None
        images.assert_not_called()
    with file_db() as session:
        usage = session.query(UserUsage).filter_by(user_id=1).one()
        assert usage.ai_images_generated == photo_count
        assert usage.ai_assistant_messages == 1
