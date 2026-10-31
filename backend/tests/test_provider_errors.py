"""Tests for client-safe AI error messages.

Gemini's error text names billing and project details (a depleted prepay
balance reads "Your prepayment credits are depleted. Please go to AI
Studio..."). It must reach the logs but never the user.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors as genai_errors

from app.services.ai.assistant import AssistantService
from app.services.ai.image_generation.service import ImageGenerationService
from app.services.ai.provider_errors import (
    AI_FAILED_MESSAGE,
    AI_UNAVAILABLE_MESSAGE,
    is_provider_unavailable,
    safe_ai_error,
)

PREPAY_TEXT = "Your prepayment credits are depleted. Please go to AI Studio"


def _api_error(code: int, message: str = PREPAY_TEXT) -> genai_errors.APIError:
    """Build the google-genai error the SDK raises for an HTTP status code."""
    error_class = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return error_class(code, {"error": {"code": code, "message": message, "status": "X"}})


# ---------------------------------------------------------------------------
# Classification and messages
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", [401, 402, 403, 429, 500, 503])
def test_account_and_outage_errors_mean_unavailable(code):
    """Billing, quota, key and Google-side failures are down for everyone."""
    assert is_provider_unavailable(_api_error(code)) is True
    assert safe_ai_error(_api_error(code), "Test") == AI_UNAVAILABLE_MESSAGE


def test_invalid_key_means_unavailable():
    """Gemini rejects a bad or revoked key with a 400 carrying API_KEY_INVALID."""
    exc = genai_errors.ClientError(
        400,
        {
            "error": {
                "code": 400,
                "message": "API key not valid. Please pass a valid API key.",
                "status": "INVALID_ARGUMENT",
                "details": [{"reason": "API_KEY_INVALID"}],
            }
        },
    )
    assert is_provider_unavailable(exc) is True
    assert safe_ai_error(exc, "Test") == AI_UNAVAILABLE_MESSAGE


@pytest.mark.parametrize(
    "exc",
    [_api_error(400, "Invalid argument"), RuntimeError("boom"), ValueError("API key not found")],
)
def test_other_errors_get_generic_message(exc):
    """Request-level errors and our own bugs get the generic failure message."""
    assert is_provider_unavailable(exc) is False
    assert safe_ai_error(exc, "Test") == AI_FAILED_MESSAGE


def test_real_error_is_logged_but_not_returned(caplog):
    """The raw provider text goes to the log with its traceback, never to the caller."""
    exc = _api_error(402)
    # In-process alembic tests run fileConfig, which disables existing loggers
    module_logger = logging.getLogger("app.services.ai.provider_errors")
    was_disabled, module_logger.disabled = module_logger.disabled, False
    try:
        with caplog.at_level(logging.ERROR, logger=module_logger.name):
            message = safe_ai_error(exc, "Assistant")
    finally:
        module_logger.disabled = was_disabled

    assert PREPAY_TEXT not in message
    record = caplog.records[-1]
    assert "[Assistant]" in record.getMessage()
    assert PREPAY_TEXT in record.getMessage()
    assert record.exc_info is not None


# ---------------------------------------------------------------------------
# Services that used to return str(e)
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_assistant_chat_hides_billing_error():
    """Genie returns the safe message when Gemini's credits run out."""
    client = MagicMock()
    client.models.generate_content.side_effect = _api_error(402)
    service = AssistantService.__new__(AssistantService)

    with patch("app.services.ai.assistant.service.get_gemini_client", return_value=client):
        result = await service.chat(message="What's for dinner?")

    assert result["type"] == "error"
    assert result["error"] == AI_UNAVAILABLE_MESSAGE


@pytest.mark.anyio
async def test_image_generation_hides_billing_error():
    """Image generation returns the safe message when Gemini's credits run out."""
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(side_effect=_api_error(402))
    service = ImageGenerationService.__new__(ImageGenerationService)

    with patch(
        "app.services.ai.image_generation.service.get_gemini_client", return_value=client
    ):
        result = await service.generate_recipe_image("Lasagna")

    assert result["success"] is False
    assert result["error"] == AI_UNAVAILABLE_MESSAGE
