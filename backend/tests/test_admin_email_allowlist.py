"""ADMIN_EXEMPT_EMAILS matches only Clerk's verified primary email."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.admin import router as admin_router
from app.api.auth import get_current_user
from app.api.auth.dependencies import require_admin, require_admin_mutator
from app.core.usage_limits import (
    get_user_monthly_limit,
    is_admin_exempt_email,
    remember_verified_primary_email,
)
from app.database.db import get_session
from app.models.user import User
from app.services.clerk_service import verified_primary_email
from app.services.user_service import UserService


def _clerk(*, primary: str, primary_status: str, secondary: str | None = None, secondary_status: str = "verified") -> dict:
    addresses = [
        {
            "id": "idn_primary",
            "email_address": primary,
            "verification": {"status": primary_status},
        }
    ]
    if secondary is not None:
        addresses.append(
            {
                "id": "idn_secondary",
                "email_address": secondary,
                "verification": {"status": secondary_status},
            }
        )
    return {"primary_email_address_id": "idn_primary", "email_addresses": addresses}


def _apply(user: User, payload: dict) -> None:
    remember_verified_primary_email(user, verified_primary_email(payload))


def test_unverified_primary_does_not_match(monkeypatch):
    monkeypatch.setenv("ADMIN_EXEMPT_EMAILS", "owner@example.com")
    user = User(id=1, clerk_id="user_unverified", email="owner@example.com", is_admin=False, subscription_tier="pro", subscription_status="active")
    _apply(user, _clerk(primary="owner@example.com", primary_status="unverified"))
    assert verified_primary_email(_clerk(primary="owner@example.com", primary_status="unverified")) is None
    assert is_admin_exempt_email(user) is False
    assert get_user_monthly_limit(user, "ai_images_generated") == 20
    with pytest.raises(HTTPException) as denied:
        require_admin(user)
    assert denied.value.status_code == 403


def test_secondary_or_changed_primary_does_not_match(monkeypatch):
    monkeypatch.setenv("ADMIN_EXEMPT_EMAILS", "owner@example.com")
    user = User(
        id=4,
        clerk_id="user_changed",
        email="owner@example.com",
        is_admin=False,
        subscription_tier="pro",
        subscription_status="active",
    )
    changed = _clerk(
        primary="other@example.com",
        primary_status="verified",
        secondary="owner@example.com",
        secondary_status="verified",
    )
    assert verified_primary_email(changed) == "other@example.com"
    _apply(user, changed)
    assert is_admin_exempt_email(user) is False
    assert get_user_monthly_limit(user, "ai_images_generated") == 20
    with pytest.raises(HTTPException) as denied:
        require_admin(user)
    assert denied.value.status_code == 403


def test_new_signup_using_a_listed_address_is_not_exempt(db_session, monkeypatch):
    monkeypatch.delenv("LEGACY_FREE_CUTOFF", raising=False)
    monkeypatch.setenv("ADMIN_EXEMPT_EMAILS", "owner@example.com")
    user = UserService(db_session).get_or_create_from_clerk("user_new_signup", "owner@example.com")
    assert user.email == "owner@example.com"
    assert is_admin_exempt_email(user) is False
    _apply(user, _clerk(primary="owner@example.com", primary_status="unverified"))
    assert user.is_legacy_free_account() is True
    assert get_user_monthly_limit(user, "ai_images_generated") == 3
    with pytest.raises(HTTPException) as view_denied:
        require_admin(user)
    assert view_denied.value.status_code == 403
    with pytest.raises(HTTPException) as mutate_denied:
        require_admin_mutator(user)
    assert mutate_denied.value.status_code == 403


def test_verified_primary_is_uncapped_and_cannot_mutate_admin(file_db, monkeypatch):
    monkeypatch.delenv("USAGE_EXEMPT_USER_IDS", raising=False)
    monkeypatch.setenv("ADMIN_EXEMPT_EMAILS", " Owner@Example.com ")
    with file_db() as session:
        user = session.get(User, 1)
        user.is_admin = False
        user.email = "stale@example.com"
        user.subscription_tier = "pro"
        user.subscription_status = "active"
        session.commit()
        user_id = user.id
    _apply(user, _clerk(primary="owner@example.com", primary_status="verified"))

    app = _admin_app(file_db, user)
    client = TestClient(app)
    assert is_admin_exempt_email(user) is True
    assert get_user_monthly_limit(user, "ai_images_generated") is None
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/status").status_code == 403
    with pytest.raises(HTTPException) as view_denied:
        require_admin(user)
    assert view_denied.value.status_code == 403
    denied = client.patch(f"/api/admin/users/{user_id}/usage-exempt", json={"usage_exempt": True})
    assert denied.status_code == 403
    assert client.patch(f"/api/admin/users/{user_id}/admin", json={"is_admin": True}).status_code == 403
    assert client.post("/api/admin/query", json={"query": "select 1"}).status_code == 403
    with pytest.raises(HTTPException) as denied:
        require_admin_mutator(user)
    assert denied.value.status_code == 403


def test_database_admin_and_id_allowlist_can_mutate(file_db, monkeypatch):
    monkeypatch.delenv("ADMIN_EXEMPT_EMAILS", raising=False)
    with file_db() as session:
        user = session.get(User, 1)
        user.is_admin = True
        session.commit()
        user_id = user.id
    app = _admin_app(file_db, user)
    client = TestClient(app)
    assert client.patch(f"/api/admin/users/{user_id}/usage-exempt", json={"usage_exempt": True}).status_code == 200

    user.is_admin = False
    monkeypatch.setenv("USAGE_EXEMPT_USER_IDS", str(user_id))
    assert client.get("/api/admin/users").status_code == 200
    assert client.get("/api/admin/status").status_code == 200
    assert client.patch(f"/api/admin/users/{user_id}/usage-exempt", json={"usage_exempt": False}).status_code == 200


def test_health_reports_an_unset_cutoff():
    """Hit /health in a subprocess so importing the app cannot reconfigure logging."""
    import subprocess
    import sys

    script = """
import os
os.environ["ENVIRONMENT"] = "development"
os.environ.pop("RAILWAY_ENVIRONMENT", None)
os.environ.pop("RAILWAY_ENVIRONMENT_NAME", None)
os.environ.pop("LEGACY_FREE_CUTOFF", None)
from fastapi.testclient import TestClient
from app.main import app
body = TestClient(app).get("/health").json()
assert body["status"] == "healthy", body
assert body["legacy_free_cutoff_configured"] is False, body
assert "LEGACY_FREE_CUTOFF is unset" in body["legacy_free_cutoff_error"]
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_clerk_verified_email_is_cached_for_five_minutes(monkeypatch):
    from app.services import clerk_service

    calls = []

    def fetch(clerk_id: str):
        calls.append(clerk_id)
        return _clerk(primary="owner@example.com", primary_status="verified")

    monkeypatch.setattr(clerk_service, "fetch_clerk_user", fetch)
    clerk_service.clear_verified_email_cache()
    assert clerk_service.cached_verified_primary_email("user_a", now=1_000) == "owner@example.com"
    assert clerk_service.cached_verified_primary_email("user_a", now=1_100) == "owner@example.com"
    assert calls == ["user_a"]
    assert clerk_service.cached_verified_primary_email("user_a", now=1_000 + clerk_service.VERIFIED_EMAIL_TTL_SECONDS) == "owner@example.com"
    assert calls == ["user_a", "user_a"]
    assert clerk_service.cached_verified_primary_email("user_b", now=1_400) == "owner@example.com"
    assert calls[-1] == "user_b"
    clerk_service.clear_verified_email_cache()


def _admin_app(file_db, user: User) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/admin")

    def session_dependency():
        with file_db() as session:
            yield session

    app.dependency_overrides[get_session] = session_dependency
    app.dependency_overrides[get_current_user] = lambda: user
    return app
