"""Feedback is stored even when the GitHub tracker cannot take it."""

import logging
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.admin import router as admin_router
from app.api.auth import get_current_user
from app.api.feedback import router as feedback_router
from app.core.rate_limit import limiter
from app.database.db import get_session
from app.models.feedback import Feedback
from app.models.user import User

BODY = "UNIQUE_FEEDBACK_BODY_9f3a the planner froze"
TOKEN = "ghp_DO_NOT_LOG_token"
ISSUE_URL = "https://github.com/owner/private-support/issues/7"


def _user(file_db, *, admin: bool = False) -> User:
    with file_db() as session:
        user = session.get(User, 1)
        user.is_admin = admin
        session.commit()
        return user


def _client(file_db, user: User) -> TestClient:
    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(feedback_router, prefix="/api/feedback")
    app.include_router(admin_router, prefix="/api/admin")

    def session_dependency():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def _payload() -> dict:
    return {
        "category": "Bug Report",
        "message": BODY,
        "metadata": {"page_url": "/meal-planner", "viewport": "390x844"},
    }


def _rows(file_db) -> list[Feedback]:
    with file_db() as session:
        return list(session.scalars(select(Feedback)))


def _repo(private: bool) -> MagicMock:
    repository = MagicMock()
    repository.json.return_value = {"private": private}
    return repository


def _issue() -> MagicMock:
    created = MagicMock()
    created.json.return_value = {"html_url": ISSUE_URL}
    return created


def _assert_log_is_safe(caplog: pytest.LogCaptureFixture) -> None:
    text = caplog.text
    assert BODY not in text
    assert TOKEN not in text


def test_unconfigured_tracker_stores_feedback(file_db, monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    monkeypatch.delenv("GITHUB_REPO", raising=False)
    caplog.set_level(logging.WARNING)

    response = _client(file_db, _user(file_db)).post("/api/feedback", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Thanks! We got your feedback."
    assert body["issue_url"] is None
    rows = _rows(file_db)
    assert len(rows) == 1
    assert rows[0].delivery_status == "stored"
    assert rows[0].error_reason == "unset_config"
    assert rows[0].issue_url is None
    assert rows[0].message == BODY
    assert rows[0].user_id == 1
    assert "unset_config" in caplog.text
    _assert_log_is_safe(caplog)


def test_public_repo_stores_feedback_and_creates_no_issue(file_db, monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    monkeypatch.setenv("GITHUB_REPO", "owner/enchanted-spoon")
    caplog.set_level(logging.WARNING)

    with patch("app.services.github_service.httpx.get", return_value=_repo(False)), patch(
        "app.services.github_service.httpx.post"
    ) as post:
        response = _client(file_db, _user(file_db)).post("/api/feedback", json=_payload())

    assert response.status_code == 200
    assert response.json()["message"] == "Thanks! We got your feedback."
    post.assert_not_called()
    rows = _rows(file_db)
    assert len(rows) == 1
    assert rows[0].delivery_status == "stored"
    assert rows[0].error_reason == "not_private"
    assert rows[0].issue_url is None
    assert "not_private" in caplog.text
    _assert_log_is_safe(caplog)


def test_github_http_error_stores_feedback(file_db, monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    monkeypatch.setenv("GITHUB_REPO", "owner/private-support")
    caplog.set_level(logging.WARNING)
    request = httpx.Request("POST", "https://api.github.com/repos/owner/private-support/issues")
    http_response = httpx.Response(502, request=request)

    def _fail(*_args, **_kwargs):
        raise httpx.HTTPStatusError("bad gateway", request=request, response=http_response)

    with patch("app.services.github_service.httpx.get", return_value=_repo(True)), patch(
        "app.services.github_service.httpx.post", side_effect=_fail
    ) as post:
        response = _client(file_db, _user(file_db)).post("/api/feedback", json=_payload())

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["issue_url"] is None
    post.assert_called_once()
    rows = _rows(file_db)
    assert rows[0].delivery_status == "stored"
    assert rows[0].error_reason == "http_error"
    assert "http_error status=502" in caplog.text
    _assert_log_is_safe(caplog)


def test_private_tracker_stores_issue_url(file_db, monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    monkeypatch.setenv("GITHUB_REPO", "owner/private-support")
    caplog.set_level(logging.WARNING)
    user = _user(file_db, admin=True)

    with patch("app.services.github_service.httpx.get", return_value=_repo(True)), patch(
        "app.services.github_service.httpx.post", return_value=_issue()
    ) as post:
        client = _client(file_db, user)
        response = client.post("/api/feedback", json=_payload())
        listed = client.get("/api/admin/feedback")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["issue_url"] == ISSUE_URL
    assert "submitted successfully" in body["message"]
    post.assert_called_once()
    rows = _rows(file_db)
    assert rows[0].delivery_status == "tracker"
    assert rows[0].issue_url == ISSUE_URL
    assert rows[0].error_reason is None
    assert rows[0].metadata_json["page_url"] == "/meal-planner"
    assert "Feedback tracker skipped" not in caplog.text
    _assert_log_is_safe(caplog)

    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert listed.json()["total"] == 1
    assert item["message"] == BODY
    assert item["issue_url"] == ISSUE_URL
    assert item["delivery_status"] == "tracker"


def test_non_admin_cannot_read_stored_feedback(file_db):
    response = _client(file_db, _user(file_db)).get("/api/admin/feedback")
    assert response.status_code == 403


def test_database_failure_returns_500(file_db, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    monkeypatch.setenv("GITHUB_REPO", "owner/private-support")
    user = _user(file_db)

    def _fail_commit(_self):
        raise SQLAlchemyError("disk")

    monkeypatch.setattr(Session, "commit", _fail_commit)
    with patch("app.services.github_service.httpx.post") as post, patch(
        "app.services.github_service.httpx.get"
    ) as get:
        response = _client(file_db, user).post("/api/feedback", json=_payload())

    assert response.status_code == 500
    assert "info@enchantedspoon.app" in response.json()["detail"]
    assert BODY not in response.text
    post.assert_not_called()
    get.assert_not_called()
    monkeypatch.undo()
    assert _rows(file_db) == []
