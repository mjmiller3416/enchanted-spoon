"""Photo import: one draft from 1–4 photos, one import unit, model mocked.

The model client is never called for real. Usage tests hit the route so the
shared recipes_imported gate is what reserves and refunds.
"""

import base64
import inspect
import io
import json
import logging
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.ai.photo_import import router as photo_router
from app.api.auth import get_current_user
from app.core.photo_import import photo_import_enabled
from app.core.rate_limit import limiter
from app.database.db import get_session
from app.dtos.recipe_generation_dtos import RecipeGeneratedDTO
from app.models.recipe import Recipe
from app.models.user import User
from app.models.user_usage import UserUsage
from app.services.ai.recipe_import import config as import_config
from app.services.ai.recipe_import.photo import (
    PhotoImportImageError,
    PhotoImportService,
    PhotoImportTooLargeError,
    prepare_recipe_photo,
)
from app.services.ai.recipe_import.service import (
    RecipeImportNotFoundError,
    RecipeImportParseError,
)
from app.services.usage_service import UsageService

pytestmark = pytest.mark.anyio


def anyio_backend():
    return "asyncio"


_BANNED = re.compile(r"\b(ai|gpt|gemini|artificial intelligence)\b", re.I)


def _jpeg(width: int = 80, height: int = 40, color: tuple[int, int, int] = (200, 100, 50)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG")
    return buffer.getvalue()


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (30, 20), (10, 20, 30, 128)).save(buffer, format="PNG")
    return buffer.getvalue()


def _recipe_payload() -> dict:
    return {
        "recipe_name": "Cardamom Buns",
        "description": "Soft buns from a card.",
        "recipe_category": "other",
        "meal_type": "breakfast",
        "diet_pref": "none",
        "prep_time": 20,
        "cook_time": 15,
        "difficulty": "Medium",
        "servings": 8,
        "ingredients": [
            {
                "ingredient_name": "Flour",
                "ingredient_category": "baking",
                "quantity": 2,
                "unit": "cup",
            }
        ],
        "directions": "Mix.\nBake.",
        "notes": None,
    }


def _model_response(payload: dict) -> SimpleNamespace:
    part = SimpleNamespace(text=json.dumps(payload), thought=False)
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]))
    usage = SimpleNamespace(
        prompt_token_count=1800,
        candidates_token_count=400,
        thoughts_token_count=0,
        cached_content_token_count=0,
    )
    return SimpleNamespace(candidates=[candidate], usage_metadata=usage)


def _image_payloads(contents: object) -> list[bytes]:
    payloads: list[bytes] = []
    if not isinstance(contents, list):
        return payloads
    for part in contents:
        inline = getattr(part, "inline_data", None)
        if inline is None or getattr(inline, "data", None) is None:
            continue
        data = inline.data
        if isinstance(data, str):
            data = base64.b64decode(data)
        payloads.append(data)
    return payloads


def _enable_import_logs(caplog) -> None:
    """Alembic's fileConfig disables loggers created before it runs."""
    for name in ("app.ai.usage", "app.services.ai.recipe_import.photo"):
        named = logging.getLogger(name)
        named.disabled = False
        caplog.set_level(logging.INFO, logger=name)


def _prompt_text(contents: object) -> str:
    chunks: list[str] = []

    def walk(value: object) -> None:
        if isinstance(value, str):
            chunks.append(value)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        text = getattr(value, "text", None)
        if isinstance(text, str):
            chunks.append(text)

    walk(contents)
    return "\n".join(chunks)


def _client(file_db, user: User | None):
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(photo_router, prefix="/api/ai/recipe-import")

    def session_dependency():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _pro_user(file_db) -> User:
    with file_db() as session:
        user = session.get(User, 1)
        user.is_admin = False
        user.subscription_tier = "pro"
        user.subscription_status = "active"
        session.commit()
        return user


def _imported(file_db) -> int:
    with file_db() as session:
        rows = session.query(UserUsage).all()
        return sum(row.recipes_imported for row in rows)


def _files(count: int, payload: bytes | None = None):
    body = payload if payload is not None else _jpeg()
    return [("images", (f"page-{index}.jpg", body, "image/jpeg")) for index in range(count)]


class TestPhotoImportConfig:
    def test_model_constant_is_the_pinned_lite_model(self):
        source = inspect.getsource(import_config)
        assert 'PHOTO_IMPORT_MODEL = "gemini-3.1-flash-lite"' in source
        assert import_config.PHOTO_IMPORT_MODEL == "gemini-3.1-flash-lite"
        assert import_config.MAX_PHOTO_COUNT == 4

    def test_prompt_uses_the_same_recipe_keys_as_url_import(self):
        for key in (
            "recipe_name",
            "recipe_category",
            "ingredients",
            "ingredient_name",
            "directions",
            "no_recipe_found",
            "to-taste",
        ):
            assert key in import_config.PHOTO_PROMPT_TEMPLATE
            assert key in import_config.PROMPT_TEMPLATE

    @pytest.mark.parametrize(
        "raw,enabled",
        [
            ("", False),
            ("false", False),
            ("no", False),
            ("true", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
        ],
    )
    def test_flag_defaults_off(self, monkeypatch, raw, enabled):
        monkeypatch.setenv("PHOTO_IMPORT_ENABLED", raw)
        assert photo_import_enabled() is enabled


class TestPhotoPreparation:
    def test_png_is_reencoded_as_jpeg(self):
        encoded = prepare_recipe_photo(_png())
        assert encoded.startswith(b"\xff\xd8")
        with Image.open(io.BytesIO(encoded)) as image:
            assert image.format == "JPEG"
            assert image.mode == "RGB"

    def test_long_edge_is_capped(self):
        encoded = prepare_recipe_photo(_jpeg(width=2000, height=800))
        with Image.open(io.BytesIO(encoded)) as image:
            assert max(image.size) == import_config.MAX_PHOTO_EDGE_PX
            assert image.size == (1600, 640)

    def test_text_is_rejected(self):
        with pytest.raises(PhotoImportImageError, match="JPEG"):
            prepare_recipe_photo(b"not a photo")

    def test_oversize_upload_is_rejected_before_decode(self):
        with pytest.raises(PhotoImportTooLargeError, match="10 MB"):
            prepare_recipe_photo(b"x" * (import_config.MAX_PHOTO_UPLOAD_BYTES + 1))


class TestPhotoImportService:
    async def test_four_photos_are_one_call_on_the_pinned_model(self, monkeypatch, caplog):
        import app.services.ai.recipe_import.photo as photo_module

        # If the call used the env-overridable name, this patch would change it.
        monkeypatch.setattr(photo_module, "MODEL_NAME", "gemini-env-override", raising=False)
        client = MagicMock()
        client.models.generate_content.return_value = _model_response(_recipe_payload())
        _enable_import_logs(caplog)

        with (
            patch.object(photo_module, "get_gemini_client", return_value=client),
            patch("cloudinary.uploader.upload") as upload,
        ):
            result = await PhotoImportService().import_from_photos(
                [_jpeg(color=(index, index, index)) for index in range(4)],
                ["italian", "mexican"],
            )

        upload.assert_not_called()
        assert client.models.generate_content.call_count == 1
        kwargs = client.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "gemini-3.1-flash-lite"
        assert kwargs["model"] == import_config.PHOTO_IMPORT_MODEL
        assert kwargs["config"]["thinking_config"] == {"thinking_level": "minimal"}
        payloads = _image_payloads(kwargs["contents"])
        assert len(payloads) == 4
        assert all(payload.startswith(b"\xff\xd8") for payload in payloads)
        prompt = _prompt_text(kwargs["contents"])
        assert "4 photos" in prompt
        assert "Do not invent" in prompt
        assert "italian|mexican" in prompt
        assert result.success is True
        assert isinstance(result.recipe, RecipeGeneratedDTO)
        assert result.recipe.recipe_name == "Cardamom Buns"
        assert result.nutrition_facts is None
        assert result.source_url is None
        assert result.reference_image_data is None
        assert result.banner_image_data is None
        assert caplog.text.count("gemini_usage") == 1
        assert "feature=photo_import" in caplog.text
        assert "model=gemini-3.1-flash-lite" in caplog.text
        assert "Cardamom" not in caplog.text
        assert b"\xff\xd8" not in caplog.text.encode()

    async def test_five_photos_never_call_the_model(self):
        client = MagicMock()
        with patch(
            "app.services.ai.recipe_import.photo.get_gemini_client",
            return_value=client,
        ):
            with pytest.raises(PhotoImportImageError, match="4"):
                await PhotoImportService().import_from_photos([b"x"] * 5, [])
        client.models.generate_content.assert_not_called()

    async def test_missing_recipe_and_bad_json(self):
        client = MagicMock()
        client.models.generate_content.return_value = _model_response(
            {"no_recipe_found": True}
        )
        with patch(
            "app.services.ai.recipe_import.photo.get_gemini_client",
            return_value=client,
        ):
            with pytest.raises(RecipeImportNotFoundError, match="that photo"):
                await PhotoImportService().import_from_photos([_jpeg()], [])

        client.models.generate_content.return_value = _model_response_text("nope")
        with patch(
            "app.services.ai.recipe_import.photo.get_gemini_client",
            return_value=client,
        ):
            with pytest.raises(RecipeImportParseError):
                await PhotoImportService().import_from_photos([_jpeg(), _jpeg()], [])


def _model_response_text(text: str) -> SimpleNamespace:
    part = SimpleNamespace(text=text, thought=False)
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]))
    usage = SimpleNamespace(
        prompt_token_count=1,
        candidates_token_count=1,
        thoughts_token_count=0,
        cached_content_token_count=0,
    )
    return SimpleNamespace(candidates=[candidate], usage_metadata=usage)


class TestPhotoImportRoute:
    def test_route_is_registered(self):
        from fastapi import FastAPI

        from app.router import api_router

        app = FastAPI()
        app.include_router(api_router)
        assert "/api/ai/recipe-import/photo" in app.openapi()["paths"]

    def test_flag_off_does_not_reserve(self, file_db, monkeypatch):
        monkeypatch.setenv("PHOTO_IMPORT_ENABLED", "false")
        user = _pro_user(file_db)
        reserved: list[str] = []
        real = UsageService.reserve

        def spy(self, field, limit):
            reserved.append(field)
            return real(self, field, limit)

        monkeypatch.setattr("app.api.auth.dependencies.UsageService.reserve", spy)
        response = _client(file_db, user).post(
            "/api/ai/recipe-import/photo",
            files=_files(1),
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Photo import is not available."
        assert _BANNED.search(response.json()["detail"]) is None
        assert reserved == []
        assert _imported(file_db) == 0

    def test_trial_required_when_flag_is_on(self, file_db, monkeypatch):
        from app.core import offer_windows

        monkeypatch.setenv("PHOTO_IMPORT_ENABLED", "true")
        cutoff = datetime(2026, 6, 1, tzinfo=timezone.utc)
        monkeypatch.setattr(offer_windows, "legacy_free_cutoff", lambda: cutoff)
        with file_db() as session:
            user = session.get(User, 1)
            user.is_admin = False
            user.subscription_tier = "free"
            user.subscription_status = "active"
            user.has_used_trial = False
            user.created_at = cutoff
            session.commit()
            assert user.usage_tier == "none"

        response = _client(file_db, user).post(
            "/api/ai/recipe-import/photo",
            files=_files(1),
        )
        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "trial_required"
        assert _imported(file_db) == 0

    def test_four_photos_count_as_one_import(self, file_db, monkeypatch, caplog):
        monkeypatch.setenv("PHOTO_IMPORT_ENABLED", "true")
        user = _pro_user(file_db)
        client = MagicMock()
        client.models.generate_content.return_value = _model_response(_recipe_payload())
        _enable_import_logs(caplog)
        reserved: list[str] = []
        real = UsageService.reserve

        def spy(self, field, limit):
            reserved.append(field)
            return real(self, field, limit)

        monkeypatch.setattr("app.api.auth.dependencies.UsageService.reserve", spy)
        with (
            patch("app.services.ai.recipe_import.photo.get_gemini_client", return_value=client),
            patch("cloudinary.uploader.upload") as upload,
        ):
            response = _client(file_db, user).post(
                "/api/ai/recipe-import/photo",
                files=_files(4),
                data={"allowed_categories": "italian, mexican"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["recipe"]["recipe_name"] == "Cardamom Buns"
        assert body["reference_image_data"] is None
        assert body["banner_image_data"] is None
        assert body["source_url"] is None
        assert body["nutrition_facts"] is None
        assert client.models.generate_content.call_count == 1
        assert len(_image_payloads(client.models.generate_content.call_args.kwargs["contents"])) == 4
        assert reserved == ["recipes_imported"]
        assert _imported(file_db) == 1
        upload.assert_not_called()
        with file_db() as session:
            assert session.query(Recipe).count() == 0
        assert caplog.text.count("gemini_usage") == 1
        assert "feature=photo_import" in caplog.text
        assert "Cardamom" not in caplog.text

    def test_five_photos_are_refunded(self, file_db, monkeypatch):
        monkeypatch.setenv("PHOTO_IMPORT_ENABLED", "true")
        user = _pro_user(file_db)
        client = MagicMock()
        with patch(
            "app.services.ai.recipe_import.photo.get_gemini_client",
            return_value=client,
        ):
            response = _client(file_db, user).post(
                "/api/ai/recipe-import/photo",
                files=_files(5, payload=b"x"),
            )
        assert response.status_code == 400
        assert "4" in response.json()["detail"]
        assert _BANNED.search(response.json()["detail"]) is None
        client.models.generate_content.assert_not_called()
        assert _imported(file_db) == 0

    def test_unreadable_photo_is_refunded(self, file_db, monkeypatch):
        monkeypatch.setenv("PHOTO_IMPORT_ENABLED", "true")
        user = _pro_user(file_db)
        response = _client(file_db, user).post(
            "/api/ai/recipe-import/photo",
            files=[("images", ("notes.txt", b"hello", "text/plain"))],
        )
        assert response.status_code == 400
        assert _BANNED.search(response.json()["detail"]) is None
        assert _imported(file_db) == 0

    def test_no_recipe_is_refunded(self, file_db, monkeypatch):
        monkeypatch.setenv("PHOTO_IMPORT_ENABLED", "true")
        user = _pro_user(file_db)
        client = MagicMock()
        client.models.generate_content.return_value = _model_response({"no_recipe_found": True})
        with patch(
            "app.services.ai.recipe_import.photo.get_gemini_client",
            return_value=client,
        ):
            response = _client(file_db, user).post(
                "/api/ai/recipe-import/photo",
                files=_files(2),
            )
        assert response.status_code == 422
        assert response.json()["detail"].startswith("No recipe was found in those photos")
        assert _BANNED.search(response.json()["detail"]) is None
        assert _imported(file_db) == 0
