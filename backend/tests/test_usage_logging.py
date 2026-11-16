"""Usage logs, request ids, billed chat calls, and chat-history cap."""

from __future__ import annotations

import io
import logging
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.request_context import (
    RequestIdMiddleware,
    current_request_id,
    request_id_var,
    user_id_var,
)
from app.dtos.assistant_dtos import AssistantMessageDTO
from app.dtos.recipe_generation_dtos import (
    GeneratedIngredientDTO,
    RecipeGeneratedDTO,
    RecipeGenerationResponseDTO,
)
from app.main import app, configure_logging
from app.models.user_usage import UserUsage
from app.services.ai.assistant import AssistantService
from app.services.ai.assistant.prompts import BASE_SYSTEM_PROMPT
from app.services.ai.assistant.service import CHAT_HISTORY_MAX_TURNS, limit_chat_history
from app.services.ai.chat_usage import ChatUsageLedger, bind_chat_usage_ledger, reset_chat_usage_ledger
from app.services.ai.usage_logging import log_usage_metadata
from app.services.usage_service import UsageService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _enable_usage_logger():
    """Alembic fileConfig in earlier tests disables loggers that already exist."""
    usage = logging.getLogger("app.ai.usage")
    was_disabled = usage.disabled
    usage.disabled = False
    yield
    usage.disabled = was_disabled


class _LoggingState:
    """Put the root logger back so one test cannot leak handlers."""

    def __init__(self) -> None:
        root = logging.getLogger()
        usage = logging.getLogger("app.ai.usage")
        self.root = root
        self.usage = usage
        self.handlers = root.handlers[:]
        self.level = root.level
        self.usage_level = usage.level
        self.propagate = usage.propagate

    def restore(self) -> None:
        self.root.handlers = self.handlers
        self.root.setLevel(self.level)
        self.usage.setLevel(self.usage_level)
        self.usage.propagate = self.propagate


def _usage_metadata() -> SimpleNamespace:
    return SimpleNamespace(
        prompt_token_count=11,
        candidates_token_count=7,
        thoughts_token_count=3,
        cached_content_token_count=1,
    )


def test_configure_logging_emits_info(monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    state = _LoggingState()
    state.root.handlers = []
    try:
        configure_logging()
        assert state.root.level == logging.INFO
        assert len(state.root.handlers) == 1
        logging.getLogger("app.ai.usage").info("gemini_usage feature=fresh")
        captured = capsys.readouterr()
        assert "gemini_usage feature=fresh" in captured.err
    finally:
        state.restore()


def test_configure_logging_respects_log_level_and_keeps_usage_at_info(monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    state = _LoggingState()
    state.root.handlers = []
    try:
        configure_logging()
        assert state.root.level == logging.WARNING
        usage = logging.getLogger("app.ai.usage")
        assert usage.level == logging.INFO
        assert usage.propagate is True
        usage.info("gemini_usage feature=warning-root")
        captured = capsys.readouterr()
        assert "gemini_usage feature=warning-root" in captured.err
    finally:
        state.restore()


def test_configure_logging_does_not_add_a_second_handler():
    state = _LoggingState()
    handler = logging.StreamHandler(io.StringIO())
    state.root.handlers = [handler]
    state.root.setLevel(logging.WARNING)
    try:
        configure_logging()
        assert state.root.handlers == [handler]
        assert state.root.level == logging.WARNING
        usage = logging.getLogger("app.ai.usage")
        assert usage.level == logging.INFO
        assert usage.propagate is True
        usage.info("gemini_usage feature=existing-handlers")
        assert "gemini_usage feature=existing-handlers" in handler.stream.getvalue()
    finally:
        state.restore()


def test_usage_line_includes_context_and_omits_prompt_text(caplog):
    caplog.set_level(logging.INFO, logger="app.ai.usage")
    secret_prompt = "do not log this prompt or user@example.com"
    response = SimpleNamespace(
        usage_metadata=_usage_metadata(),
        text=secret_prompt,
    )
    request_token = request_id_var.set("req-42")
    user_token = user_id_var.set(42)
    try:
        log_usage_metadata(
            "assistant",
            "gemini-test",
            response,
            photo_count=2,
            image_count=1,
            fallback=True,
        )
    finally:
        request_id_var.reset(request_token)
        user_id_var.reset(user_token)

    line = caplog.text
    assert "gemini_usage" in line
    assert "feature=assistant" in line
    assert "model=gemini-test" in line
    assert "prompt_tokens=11" in line
    assert "candidate_tokens=7" in line
    assert "thought_tokens=3" in line
    assert "cached_tokens=1" in line
    assert "user_id=42" in line
    assert "photo_count=2" in line
    assert "image_count=1" in line
    assert "fallback=true" in line
    assert "request_id=req-42" in line
    assert secret_prompt not in line
    assert "user@example.com" not in line


def test_usage_line_defaults_missing_context(caplog):
    caplog.set_level(logging.INFO, logger="app.ai.usage")
    request_token = request_id_var.set(None)
    user_token = user_id_var.set(None)
    try:
        log_usage_metadata("cooking_tips", "gemini-test", SimpleNamespace())
    finally:
        request_id_var.reset(request_token)
        user_id_var.reset(user_token)

    assert "user_id=none" in caplog.text
    assert "photo_count=0" in caplog.text
    assert "image_count=0" in caplog.text
    assert "fallback=false" in caplog.text
    assert "request_id=none" in caplog.text


def test_request_id_middleware_sets_and_echoes_header():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/ping")
    def ping():
        return {"request_id": current_request_id()}

    client = TestClient(app)

    supplied = client.get("/ping", headers={"X-Request-ID": "abc-123"})
    assert supplied.status_code == 200
    assert supplied.headers["X-Request-ID"] == "abc-123"
    assert supplied.json()["request_id"] == "abc-123"

    generated = client.get("/ping")
    echoed = generated.headers["X-Request-ID"]
    parsed = uuid.UUID(echoed)
    assert parsed.version == 4
    assert generated.json()["request_id"] == echoed

    rejected = client.get("/ping", headers={"X-Request-ID": "bad id\ninjected"})
    assert "bad id" not in rejected.headers["X-Request-ID"]
    assert uuid.UUID(rejected.headers["X-Request-ID"]).version == 4
    assert "injected" not in rejected.json()["request_id"]


def test_app_echoes_request_id_header():
    client = TestClient(app)
    response = client.get("/health", headers={"X-Request-ID": "health-trace"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "health-trace"


def _text_part(text: str) -> MagicMock:
    part = MagicMock()
    part.thought = False
    part.function_call = None
    part.text = text
    return part


def _function_call_part(name: str, args: dict) -> MagicMock:
    function_call = MagicMock()
    function_call.name = name
    function_call.args = args
    part = MagicMock()
    part.thought = False
    part.function_call = function_call
    part.text = None
    return part


def _response(parts: list) -> MagicMock:
    content = MagicMock()
    content.parts = parts
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    response.usage_metadata = _usage_metadata()
    return response


def _message_count(file_db) -> int:
    with file_db() as session:
        usage = session.query(UserUsage).filter_by(user_id=1).one()
        return usage.ai_assistant_messages


def _reserve_first_call(file_db, limit: int = 100) -> None:
    with file_db() as session:
        UsageService(session, user_id=1).reserve("ai_assistant_messages", limit)


@pytest.mark.anyio
async def test_chat_with_two_billed_calls_increments_usage_twice(file_db, caplog):
    """A tool follow-up is a second billed call. The first was already reserved."""
    caplog.set_level(logging.INFO, logger="app.ai.usage")
    _reserve_first_call(file_db)
    client = MagicMock()
    client.models.generate_content.side_effect = [
        _response([_function_call_part("suggest_recipes", {"mood_or_vibe": "cozy"})]),
        _response([_text_part("Try a cozy soup.")]),
    ]
    service = AssistantService.__new__(AssistantService)
    user_token = user_id_var.set(1)
    request_token = request_id_var.set("chat-req")

    with file_db() as session:
        token = bind_chat_usage_ledger(
            ChatUsageLedger(
                session=session,
                user_id=1,
                field="ai_assistant_messages",
                limit=100,
                window=None,
            )
        )
        try:
            with (
                patch("app.services.ai.assistant.service.get_gemini_client", return_value=client),
                patch("app.services.ai.assistant.generators.get_gemini_client", return_value=client),
            ):
                result = await service.chat(message="something cozy")
        finally:
            reset_chat_usage_ledger(token)
            user_id_var.reset(user_token)
            request_id_var.reset(request_token)

    assert result["type"] == "suggestions"
    assert result["response"] == "Try a cozy soup."
    assert client.models.generate_content.call_count == 2
    assert _message_count(file_db) == 2
    assert caplog.text.count("gemini_usage") == 2
    assert "feature=assistant " in caplog.text
    assert "feature=assistant_followup" in caplog.text
    assert "user_id=1" in caplog.text
    assert "request_id=chat-req" in caplog.text


@pytest.mark.anyio
async def test_single_billed_chat_call_is_not_counted_twice(file_db):
    _reserve_first_call(file_db)
    client = MagicMock()
    client.models.generate_content.return_value = _response([_text_part("Soup is great.")])
    service = AssistantService.__new__(AssistantService)

    with file_db() as session:
        token = bind_chat_usage_ledger(
            ChatUsageLedger(
                session=session,
                user_id=1,
                field="ai_assistant_messages",
                limit=100,
                window=None,
            )
        )
        try:
            with patch("app.services.ai.assistant.service.get_gemini_client", return_value=client):
                result = await service.chat(message="hi")
        finally:
            reset_chat_usage_ledger(token)

    assert result["type"] == "chat"
    assert client.models.generate_content.call_count == 1
    assert _message_count(file_db) == 1


@pytest.mark.anyio
async def test_recipe_retry_counts_each_billed_attempt(file_db):
    from app.services.ai.recipe_generation.service import RecipeParseError

    recipe = RecipeGeneratedDTO(
        recipe_name="Tacos",
        directions="Cook.",
        ingredients=[
            GeneratedIngredientDTO(
                ingredient_name="Tortillas", ingredient_category="bakery"
            )
        ],
    )
    service = AssistantService.__new__(AssistantService)
    with file_db() as session:
        token = bind_chat_usage_ledger(
            ChatUsageLedger(
                session=session,
                user_id=1,
                field="ai_assistant_messages",
                limit=100,
                window=None,
            )
        )
        try:
            with patch(
                "app.services.ai.assistant.generators.get_recipe_generation_service"
            ) as get_service:
                get_service.return_value.generate = AsyncMock(
                    side_effect=[
                        RecipeParseError("truncated"),
                        RecipeGenerationResponseDTO(success=True, recipe=recipe),
                    ]
                )
                result = await service._generate_recipe_from_args({"recipe_name": "Tacos"})
        finally:
            reset_chat_usage_ledger(token)

    assert result is not None
    assert result.recipe_name == "Tacos"
    assert get_service.return_value.generate.await_count == 2
    assert _message_count(file_db) == 2


def test_history_is_truncated_to_ten_turns_and_keeps_system_prompt():
    history = []
    for index in range(12):
        history.append(AssistantMessageDTO(role="user", content=f"user-{index}"))
        history.append(AssistantMessageDTO(role="assistant", content=f"assistant-{index}"))

    service = AssistantService.__new__(AssistantService)
    contents = service._build_contents("kitchen context", history, "current question")
    texts = [item["parts"][0]["text"] for item in contents]

    assert texts[0] == BASE_SYSTEM_PROMPT
    assert "Genie" in texts[1]
    assert "kitchen context" in texts
    assert texts[-1] == "current question"
    assert "user-0" not in texts
    assert "user-1" not in texts
    assert "assistant-0" not in texts
    assert "user-2" in texts
    assert "assistant-11" in texts
    history_texts = texts[4:-1]
    assert len(history_texts) == CHAT_HISTORY_MAX_TURNS * 2

    short = limit_chat_history(history[:4])
    assert short is not None
    assert [message.content for message in short] == [
        "user-0",
        "assistant-0",
        "user-1",
        "assistant-1",
    ]
    assert limit_chat_history(None) is None
