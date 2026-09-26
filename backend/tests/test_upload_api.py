"""Tests for the recipe image upload API (size caps and error hygiene)."""

import base64
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import upload as upload_module
from app.api.auth import get_current_user
from app.database.db import get_session
from app.models.user import User


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(upload_module.router, prefix="/api/upload")
    user = MagicMock(spec=User)
    user.id = 1
    app.dependency_overrides[get_session] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _owned_recipe():
    return patch.object(upload_module, "_resolve_image_key", return_value="a" * 32)


class TestUploadLimits:
    def test_oversized_file_is_rejected_before_upload(self):
        with _owned_recipe(), patch.object(upload_module, "MAX_IMAGE_BYTES", 10), patch(
            "cloudinary.uploader.upload"
        ) as upload:
            resp = _client().post(
                "/api/upload",
                files={"file": ("big.jpg", b"x" * 11, "image/jpeg")},
                data={"recipeId": "1"},
            )
        assert resp.status_code == 413
        upload.assert_not_called()

    def test_oversized_base64_is_rejected(self):
        with _owned_recipe(), patch.object(upload_module, "MAX_BASE64_CHARS", 8), patch(
            "cloudinary.uploader.upload"
        ) as upload:
            resp = _client().post(
                "/api/upload/base64",
                data={"image_data": base64.b64encode(b"x" * 30).decode(), "recipeId": "1"},
            )
        assert resp.status_code == 413
        upload.assert_not_called()

    def test_cloudinary_failure_does_not_leak_details(self):
        with _owned_recipe(), patch(
            "cloudinary.uploader.upload", side_effect=RuntimeError("api_secret=abc123")
        ):
            resp = _client().post(
                "/api/upload",
                files={"file": ("ok.jpg", b"img", "image/jpeg")},
                data={"recipeId": "1"},
            )
        assert resp.status_code == 502
        assert "abc123" not in resp.text

    def test_valid_upload_returns_url(self):
        with _owned_recipe(), patch(
            "cloudinary.uploader.upload",
            return_value={"secure_url": "https://x/y.jpg", "public_id": "y"},
        ):
            resp = _client().post(
                "/api/upload",
                files={"file": ("ok.jpg", b"img", "image/jpeg")},
                data={"recipeId": "1", "imageType": "banner"},
            )
        assert resp.status_code == 200
        assert resp.json()["path"] == "https://x/y.jpg"
