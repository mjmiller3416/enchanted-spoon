"""Sentry wiring: off without a DSN, one event per failure, user id only."""

import logging
from unittest.mock import MagicMock

import pytest
import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sentry_sdk.transport import Transport

from app.api.auth import get_current_user
from app.api.errors import internal_error
from app.core import observability
from app.models.user import User


def test_disabled_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    init = MagicMock()
    monkeypatch.setattr(observability.sentry_sdk, "init", init)

    assert observability.init_sentry() is False
    init.assert_not_called()


def test_init_uses_railway_release_and_environment(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://key@o0.ingest.sentry.io/0")
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "abc123")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.delenv("SENTRY_ENVIRONMENT", raising=False)
    init = MagicMock()
    monkeypatch.setattr(observability.sentry_sdk, "init", init)

    assert observability.init_sentry() is True
    kwargs = init.call_args.kwargs
    assert kwargs["release"] == "abc123"
    assert kwargs["environment"] == "production"
    assert kwargs["send_default_pii"] is False
    assert kwargs["max_request_body_size"] == "never"


class _ListTransport(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.events: list[dict] = []

    def capture_envelope(self, envelope) -> None:
        self.events.extend(
            item.payload.json for item in envelope.items if item.type == "event"
        )


@pytest.fixture()
def captured_events():
    """Route a real Sentry client into a list for the duration of a test."""
    transport = _ListTransport()
    events = transport.events
    # In-process alembic tests run fileConfig, which disables existing loggers
    api_logger = logging.getLogger("app.api")
    was_disabled, api_logger.disabled = api_logger.disabled, False
    sentry_sdk.init(
        dsn="https://key@o0.ingest.sentry.io/0",
        transport=transport,
        send_default_pii=False,
        max_request_body_size="never",
        before_send=observability._before_send,
    )
    yield events
    api_logger.disabled = was_disabled
    sentry_sdk.get_client().close()
    sentry_sdk.init()  # back to a disabled client


def _app(user: User) -> TestClient:
    app = FastAPI()

    @app.get("/boom")
    def boom(current_user: User = Depends(get_current_user)):
        observability.set_user(current_user.id)
        try:
            raise ValueError("database exploded")
        except ValueError:
            raise internal_error()

    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=False)


def test_handled_500_is_reported_once_with_the_real_cause(captured_events):
    user = User(id=7, clerk_id="c7", email="someone@example.com", name="Someone")

    response = _app(user).get("/boom")
    sentry_sdk.flush()

    assert response.status_code == 500
    assert len(captured_events) == 1
    event = captured_events[0]
    exception_types = [e["type"] for e in event["exception"]["values"]]
    assert "ValueError" in exception_types
    assert "HTTPException" not in exception_types
    assert event["user"] == {"id": "7"}
    assert "someone@example.com" not in str(event.get("user"))
