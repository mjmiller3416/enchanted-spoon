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


# ---------------------------------------------------------------------------
# add_to_shopping_list tool
# ---------------------------------------------------------------------------

def _shopping_result(added=(), reactivated=(), already_listed=()):
    from app.dtos.shopping_dtos import ManualItemsAddResultDTO, ShoppingItemResponseDTO

    def item(i, name):
        return ShoppingItemResponseDTO(
            id=i, ingredient_name=name, quantity=1, source="manual"
        )

    return ManualItemsAddResultDTO(
        added=[item(i, n) for i, n in enumerate(added, 1)],
        reactivated=[item(i, n) for i, n in enumerate(reactivated, 100)],
        already_listed=list(already_listed),
    )


async def test_shopping_tool_writes_items_and_reports_outcome():
    """The write happens first and its real outcome is handed to the model."""
    service = _make_service()
    service._finalize_after_tool_call = MagicMock(return_value="Done! 🛒")
    result = _shopping_result(added=["Milk"], already_listed=["Eggs"])
    adder = MagicMock(return_value=result)

    out = await service._handle_function_call(
        "add_to_shopping_list",
        {"items": [
            {"name": "Milk", "category": "dairy"},
            {"name": "Eggs", "quantity": 12},
        ]},
        None,
        [],
        None,
        adder,
    )

    dtos = adder.call_args.args[0]
    assert [d.ingredient_name for d in dtos] == ["Milk", "Eggs"]
    assert dtos[0].category == "dairy" and dtos[0].quantity == 1
    assert dtos[1].category == "other" and dtos[1].quantity == 12
    assert service._finalize_after_tool_call.call_args.kwargs["result"] == {
        "added": ["Milk"],
        "moved_back_to_need": [],
        "already_on_list": ["Eggs"],
    }
    assert out["type"] == "shopping"
    assert out["response"] == "Done! 🛒"
    assert out["shopping_update"] is result


async def test_shopping_tool_drops_invalid_and_repeated_items():
    service = _make_service()
    service._finalize_after_tool_call = MagicMock(return_value="ok")
    adder = MagicMock(return_value=_shopping_result(added=["Milk"]))

    await service._handle_function_call(
        "add_to_shopping_list",
        {"items": [
            {"name": "Milk", "category": "not-a-category"},
            {"name": "  milk "},
            {"name": ""},
            {"quantity": 2},
        ]},
        None,
        [],
        None,
        adder,
    )

    dtos = adder.call_args.args[0]
    assert len(dtos) == 1
    assert dtos[0].ingredient_name == "Milk" and dtos[0].category == "other"


async def test_shopping_tool_failed_write_never_claims_success():
    """A failed write returns a canned apology without asking the model."""
    service = _make_service()
    service._finalize_after_tool_call = MagicMock()

    out = await service._handle_function_call(
        "add_to_shopping_list",
        {"items": [{"name": "Milk"}]},
        None,
        [],
        None,
        MagicMock(return_value=None),
    )

    service._finalize_after_tool_call.assert_not_called()
    assert out["type"] == "chat"
    assert "couldn't update" in out["response"]
    assert "shopping_update" not in out


async def test_shopping_tool_without_writer_does_not_crash():
    """Callers that don't supply a writer (legacy endpoint) get a graceful reply."""
    service = _make_service()

    out = await service._handle_function_call(
        "add_to_shopping_list", {"items": [{"name": "Milk"}]}, None, [], None
    )

    assert out["type"] == "chat"
    assert "shopping_update" not in out


async def test_shopping_tool_fallback_text_describes_outcome():
    service = _make_service()

    text = service._describe_shopping_update(
        {"added": ["Milk", "Bread"], "moved_back_to_need": ["Eggs"], "already_on_list": ["Butter"]}
    )

    assert text == "Added Milk, Bread and Eggs to your shopping list! 🛒 Butter is already on there."
