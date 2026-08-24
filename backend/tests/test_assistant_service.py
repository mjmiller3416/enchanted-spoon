"""Tests for the AI assistant response processing.

Regression coverage for the Gemini 3.x behavior change where the model emits a
conversational preamble text part *before* the function_call part. The response
processor must prioritize the function call over the preamble text, otherwise
the preamble ("Here are some ideas! 🔍") is returned as a plain chat reply and
the tool (e.g. suggest_recipes) never executes.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.assistant import AssistantService

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_part(text: str):
    """A response part containing only text."""
    part = MagicMock()
    part.thought = False
    part.function_call = None
    part.text = text
    return part


def _function_call_part(name: str, args: dict):
    """A response part containing only a function call."""
    fc = MagicMock()
    fc.name = name
    fc.args = args

    part = MagicMock()
    part.thought = False
    part.function_call = fc
    part.text = None
    return part


def _make_response(parts: list):
    """Wrap parts in a mock Gemini GenerateContentResponse."""
    content = MagicMock()
    content.parts = parts

    candidate = MagicMock()
    candidate.content = content

    response = MagicMock()
    response.candidates = [candidate]
    return response


def _make_service() -> AssistantService:
    """Build a service instance without running __init__ (skips client setup)."""
    return AssistantService.__new__(AssistantService)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_function_call_takes_precedence_over_preamble_text():
    """Preamble text before a function call must not short-circuit the tool."""
    service = _make_service()
    service._handle_function_call = AsyncMock(
        return_value={"type": "suggestions", "response": "..."}
    )

    response = _make_response(
        [
            _text_part("Here are some ideas! 🔍"),
            _function_call_part("suggest_recipes", {"main_ingredient": "chicken"}),
        ]
    )

    result = await service._process_response(response, user_context_data=None, contents=[])

    service._handle_function_call.assert_called_once()
    called_tool = service._handle_function_call.call_args.args[0]
    called_args = service._handle_function_call.call_args.args[1]
    assert called_tool == "suggest_recipes"
    assert called_args == {"main_ingredient": "chicken"}
    assert result["type"] == "suggestions"


async def test_function_call_handled_when_it_is_the_only_part():
    """Gemini 2.x style: a bare function_call part still routes to the tool."""
    service = _make_service()
    service._handle_function_call = AsyncMock(
        return_value={"type": "recipe", "response": "..."}
    )

    response = _make_response(
        [_function_call_part("create_recipe", {"recipe_name": "Tacos"})]
    )

    await service._process_response(response, user_context_data=None, contents=[])

    service._handle_function_call.assert_called_once()
    assert service._handle_function_call.call_args.args[0] == "create_recipe"


async def test_plain_text_returns_chat():
    """A text-only response (casual conversation) returns a chat reply."""
    service = _make_service()

    response = _make_response([_text_part("Honestly, I'm doing great! 💛")])

    result = await service._process_response(response, user_context_data=None, contents=[])

    assert result["type"] == "chat"
    assert result["response"] == "Honestly, I'm doing great! 💛"


async def test_thought_parts_are_ignored():
    """Thinking parts must not be mistaken for the conversational reply."""
    service = _make_service()

    thought = MagicMock()
    thought.thought = True
    thought.function_call = None
    thought.text = "internal reasoning..."

    response = _make_response([thought, _text_part("The real answer ✨")])

    result = await service._process_response(response, user_context_data=None, contents=[])

    assert result["type"] == "chat"
    assert result["response"] == "The real answer ✨"
