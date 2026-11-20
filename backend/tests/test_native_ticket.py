"""Native shell session JWTs are exchanged for a one-minute sign-in ticket."""

import base64
import json
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.native_auth import router as native_auth_router
from app.core.auth_config import get_auth_settings
from app.core.rate_limit import ip_limiter, limiter
from app.router import api_router
from app.services import clerk_service


def _b64u(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    raw = value.to_bytes(length, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@pytest.fixture()
def clerk_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": "native-ticket-test",
        "n": _b64u(numbers.n),
        "e": _b64u(numbers.e),
    }
    return pem, jwk


def _token(pem: str, claims: dict) -> str:
    encoded = jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "native-ticket-test"})
    assert isinstance(encoded, str)
    return encoded


class _ClerkResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload


@pytest.fixture()
def client(monkeypatch, clerk_keys):
    pem, jwk = clerk_keys
    settings = get_auth_settings()
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test_secret")
    monkeypatch.setattr(settings, "auth_disabled", True)

    async def jwks(_settings=None):
        return {"keys": [jwk]}

    monkeypatch.setattr("app.api.auth.session_jwt.get_clerk_jwks", jwks)

    calls: dict[str, list[dict[str, Any]]] = {"post": [], "delete": []}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["post"].append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _ClerkResponse(
            200,
            {
                "object": "sign_in_token",
                "id": "sit_secret_id",
                "user_id": json["user_id"],
                "token": "ticket_value",
                "status": "pending",
                "url": "https://clerk.example.test/sign-in?__clerk_ticket=ticket_value",
            },
        )

    def fake_delete(url, headers=None, timeout=None):
        calls["delete"].append({"url": url, "headers": headers, "timeout": timeout})
        return _ClerkResponse(200, {"object": "session", "id": "sess_abc", "status": "revoked"})

    monkeypatch.setattr(clerk_service.httpx, "post", fake_post)
    monkeypatch.setattr(clerk_service.httpx, "delete", fake_delete)

    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(native_auth_router, prefix="/api/auth")
    return TestClient(app), calls, pem


def test_route_is_registered():
    app = FastAPI()
    app.include_router(api_router)
    assert "/api/auth/native-ticket" in app.openapi()["paths"]


def test_valid_session_jwt_returns_only_the_ticket(client, caplog):
    http, calls, pem = client
    session_jwt = _token(pem, {"sub": "user_abc", "sid": "sess_abc"})
    caplog.set_level("DEBUG")

    response = http.post(
        "/api/auth/native-ticket",
        headers={"Authorization": f"Bearer {session_jwt}"},
    )

    assert response.status_code == 200
    assert response.json() == {"ticket": "ticket_value"}
    body = response.text
    assert "sk_test_secret" not in body
    assert session_jwt not in body
    assert "sit_secret_id" not in body
    assert "__clerk_ticket" not in body
    assert "user_abc" not in body

    assert calls["post"] == [
        {
            "url": "https://api.clerk.com/v1/sign_in_tokens",
            "headers": {"Authorization": "Bearer sk_test_secret"},
            "json": {"user_id": "user_abc", "expires_in_seconds": 60},
            "timeout": clerk_service.CLERK_API_TIMEOUT,
        }
    ]
    assert calls["delete"] == [
        {
            "url": "https://api.clerk.com/v1/sessions/sess_abc",
            "headers": {"Authorization": "Bearer sk_test_secret"},
            "timeout": clerk_service.CLERK_API_TIMEOUT,
        }
    ]
    assert "sk_test_secret" not in caplog.text
    assert session_jwt not in caplog.text
    assert "ticket_value" not in caplog.text


def test_missing_and_invalid_jwts_are_rejected(client):
    http, calls, pem = client

    missing = http.post("/api/auth/native-ticket")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Missing authentication token"

    garbage = http.post(
        "/api/auth/native-ticket",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert garbage.status_code == 401
    assert garbage.json()["detail"] == "Invalid authentication token"
    assert "not-a-jwt" not in garbage.text

    no_session = _token(pem, {"sub": "user_abc"})
    unsigned_session = http.post(
        "/api/auth/native-ticket",
        headers={"Authorization": f"Bearer {no_session}"},
    )
    assert unsigned_session.status_code == 401

    tampered = _token(pem, {"sub": "user_abc", "sid": "sess_abc"})
    flipped = tampered[:-4] + ("AAAA" if not tampered.endswith("AAAA") else "BBBB")
    bad_signature = http.post(
        "/api/auth/native-ticket",
        headers={"Authorization": f"Bearer {flipped}"},
    )
    assert bad_signature.status_code == 401
    assert calls["post"] == []
    assert calls["delete"] == []


def test_auth_disabled_does_not_mint_a_ticket_without_a_jwt(client):
    http, calls, _pem = client
    response = http.post("/api/auth/native-ticket")
    assert response.status_code == 401
    assert calls["post"] == []


def test_clerk_error_body_is_not_echoed(client, monkeypatch, caplog):
    http, _calls, pem = client

    def fake_post(url, headers=None, json=None, timeout=None):
        return _ClerkResponse(
            422,
            {"errors": [{"message": "leaked sk_test_secret", "long_message": "ticket_value"}]},
        )

    monkeypatch.setattr(clerk_service.httpx, "post", fake_post)
    caplog.set_level("DEBUG")
    session_jwt = _token(pem, {"sub": "user_abc", "sid": "sess_abc"})

    response = http.post(
        "/api/auth/native-ticket",
        headers={"Authorization": f"Bearer {session_jwt}"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Sign-in could not be completed. Please try again."}
    assert "sk_test_secret" not in response.text
    assert "ticket_value" not in response.text
    assert session_jwt not in response.text
    assert "sk_test_secret" not in caplog.text
    assert session_jwt not in caplog.text
    assert "ticket_value" not in caplog.text


def test_revoke_failure_still_returns_the_ticket(client, monkeypatch):
    http, calls, pem = client

    def boom(url, headers=None, timeout=None):
        calls["delete"].append({"url": url})
        raise httpx.ConnectError("down")

    monkeypatch.setattr(clerk_service.httpx, "delete", boom)
    session_jwt = _token(pem, {"sub": "user_abc", "sid": "sess_abc"})
    response = http.post(
        "/api/auth/native-ticket",
        headers={"Authorization": f"Bearer {session_jwt}"},
    )

    assert response.status_code == 200
    assert response.json() == {"ticket": "ticket_value"}
    assert calls["delete"][0]["url"] == "https://api.clerk.com/v1/sessions/sess_abc"
    assert "sk_test_secret" not in response.text
