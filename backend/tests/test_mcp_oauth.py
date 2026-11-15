"""The ChatGPT connector's OAuth 2.1 server, end to end.

Walks the flow ChatGPT runs: 401 + discovery, dynamic client registration,
the consent page's check and decision (signed in through Clerk, here an
overridden ``get_current_user``; signed out gets 401 and the page's Clerk
middleware sends the person to sign in), the token exchange with PKCE, MCP
calls with the token, refresh rotation, revocation, expiry, the kill switch,
and Settings' connected apps.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app.api.auth import get_current_user
from app.database.db import get_session
from app.main import app
from app.models.oauth import OAuthToken
from app.models.user import User

ORIGIN = "https://es.test"
REDIRECT = "https://chatgpt.com/connector_platform_oauth_redirect"
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"}


def pkce() -> tuple[str, str]:
    """A (verifier, S256 challenge) pair."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


@pytest.fixture()
def factory(file_db, monkeypatch):
    """A file-backed DB whose user 1 is signed in (admin, so never read-only), and a public origin."""
    monkeypatch.setenv("MCP_PUBLIC_URL", ORIGIN)
    monkeypatch.delenv("MCP_ENABLED", raising=False)
    monkeypatch.delenv("MCP_AUTHORIZE_URL", raising=False)
    with file_db() as session:
        session.get(User, 1).is_admin = True
        session.add(User(id=2, clerk_id="file_db_user_2", email="u2@example.com", is_admin=True))
        session.commit()

    def _session():
        session = file_db()
        try:
            yield session
        finally:
            session.close()

    def _signed_in():
        with file_db() as session:
            return session.get(User, 1)

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = _signed_in
    yield file_db
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def client(factory) -> TestClient:
    return TestClient(app)


def register(client: TestClient, method: str = "none") -> dict:
    r = client.post(
        "/api/oauth/register",
        json={"redirect_uris": [REDIRECT], "client_name": "ChatGPT", "token_endpoint_auth_method": method},
    )
    assert r.status_code == 201, r.text
    return r.json()


def authorize_params(client_id: str, challenge: str, **extra) -> dict:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "xyz-state",
        "scope": "mcp",
        "resource": f"{ORIGIN}/api/mcp",
    }
    params.update(extra)
    return params


def get_code(client: TestClient, client_id: str, challenge: str) -> str:
    r = client.post("/api/oauth/authorize", json={**authorize_params(client_id, challenge), "decision": "allow"})
    assert r.status_code == 200, r.text
    query = parse_qs(urlsplit(r.json()["redirect_to"]).query)
    assert query["iss"] == [ORIGIN]
    assert query["state"] == ["xyz-state"]
    return query["code"][0]


def exchange(client: TestClient, client_id: str, code: str, verifier: str, **extra):
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": REDIRECT,
        "code_verifier": verifier,
        "resource": f"{ORIGIN}/api/mcp",
    }
    data.update(extra)
    return client.post("/api/oauth/token", data=data)


def connect(client: TestClient) -> tuple[str, dict]:
    """Register, consent and exchange; returns (client_id, token response)."""
    client_id = register(client)["client_id"]
    verifier, challenge = pkce()
    r = exchange(client, client_id, get_code(client, client_id, challenge), verifier)
    assert r.status_code == 200, r.text
    return client_id, r.json()


def rpc(client: TestClient, method: str, params: dict | None = None, token: str | None = None):
    headers = dict(MCP_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return client.post("/api/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}, headers=headers)


# ── Discovery ───────────────────────────────────────────────────────────────
def test_mcp_without_a_token_points_at_the_metadata(client):
    r = rpc(client, "initialize")
    assert r.status_code == 401
    header = r.headers["www-authenticate"]
    assert header.startswith("Bearer ")
    assert f'resource_metadata="{ORIGIN}/.well-known/oauth-protected-resource"' in header
    assert 'scope="mcp"' in header


def test_discovery_documents(client):
    for path in ("/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/api/mcp"):
        doc = client.get(path).json()
        assert doc["resource"] == f"{ORIGIN}/api/mcp"
        assert doc["authorization_servers"] == [ORIGIN]
        assert doc["scopes_supported"] == ["mcp"]
        assert doc["bearer_methods_supported"] == ["header"]

    meta = client.get("/.well-known/oauth-authorization-server").json()
    assert meta["issuer"] == ORIGIN
    assert meta["authorization_endpoint"] == f"{ORIGIN}/oauth/authorize"
    assert meta["token_endpoint"] == f"{ORIGIN}/api/oauth/token"
    assert meta["registration_endpoint"] == f"{ORIGIN}/api/oauth/register"
    assert meta["revocation_endpoint"] == f"{ORIGIN}/api/oauth/revoke"
    assert meta["code_challenge_methods_supported"] == ["S256"]
    assert meta["authorization_response_iss_parameter_supported"] is True
    assert set(meta["token_endpoint_auth_methods_supported"]) == {"none", "client_secret_post", "client_secret_basic"}
    assert "client_id_metadata_document_supported" not in meta
    assert client.get("/.well-known/openid-configuration").status_code == 404


# ── Registration ────────────────────────────────────────────────────────────
def test_registration(client):
    public = register(client, "none")
    assert "client_secret" not in public
    assert public["redirect_uris"] == [REDIRECT]
    assert public["token_endpoint_auth_method"] == "none"
    assert isinstance(public["client_id_issued_at"], int)

    confidential = register(client, "client_secret_basic")
    assert len(confidential["client_secret"]) >= 43

    default = client.post("/api/oauth/register", json={"redirect_uris": [REDIRECT]}).json()
    assert default["token_endpoint_auth_method"] == "client_secret_basic"
    assert "client_secret" in default

    for bad in (["https://evil.example/cb"], ["http://chatgpt.com/cb"], [], "https://chatgpt.com/x"):
        r = client.post("/api/oauth/register", json={"redirect_uris": bad})
        assert r.status_code == 400
        assert r.json()["error"] == "invalid_redirect_uri"
    # Local testing redirects are allowed
    local = client.post("/api/oauth/register", json={"redirect_uris": ["http://localhost:6274/callback"]})
    assert local.status_code == 201


# ── Authorization ───────────────────────────────────────────────────────────
def test_authorize_on_the_backend_sends_the_browser_to_the_consent_page(client):
    client_id = register(client)["client_id"]
    _, challenge = pkce()
    r = client.get("/api/oauth/authorize", params=authorize_params(client_id, challenge), follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].startswith(f"{ORIGIN}/oauth/authorize?")
    assert f"client_id={client_id}" in r.headers["location"]


def test_consent_page_check(client):
    client_id = register(client)["client_id"]
    _, challenge = pkce()
    ok = client.get("/api/oauth/authorize/check", params=authorize_params(client_id, challenge)).json()
    assert ok == {"status": "ok", "client_name": "ChatGPT", "redirect_to": None, "message": None}

    unknown = client.get("/api/oauth/authorize/check", params=authorize_params("nope", challenge)).json()
    assert unknown["status"] == "error" and unknown["redirect_to"] is None

    wrong_redirect = client.get(
        "/api/oauth/authorize/check",
        params=authorize_params(client_id, challenge, redirect_uri="https://chatgpt.com/other"),
    ).json()
    assert wrong_redirect["status"] == "error" and wrong_redirect["redirect_to"] is None

    no_pkce = client.get(
        "/api/oauth/authorize/check", params=authorize_params(client_id, challenge, code_challenge_method="plain")
    ).json()
    assert no_pkce["status"] == "redirect"
    query = parse_qs(urlsplit(no_pkce["redirect_to"]).query)
    assert query["error"] == ["invalid_request"]
    assert query["iss"] == [ORIGIN]
    assert query["state"] == ["xyz-state"]

    wrong_resource = client.get(
        "/api/oauth/authorize/check", params=authorize_params(client_id, challenge, resource="https://other.test/mcp")
    ).json()
    assert parse_qs(urlsplit(wrong_resource["redirect_to"]).query)["error"] == ["invalid_target"]

    trailing_slash = client.get(
        "/api/oauth/authorize/check", params=authorize_params(client_id, challenge, resource=f"{ORIGIN}/api/mcp/")
    ).json()
    assert trailing_slash["status"] == "ok"


def test_consent_needs_the_app_sign_in(client):
    """Signed out, the decision is refused (the page's Clerk middleware signs the person in first)."""
    app.dependency_overrides.pop(get_current_user)
    client_id = register(client)["client_id"]
    _, challenge = pkce()
    r = client.post("/api/oauth/authorize", json={**authorize_params(client_id, challenge), "decision": "allow"})
    assert r.status_code == 401


def test_cancel_returns_access_denied(client):
    client_id = register(client)["client_id"]
    _, challenge = pkce()
    r = client.post("/api/oauth/authorize", json={**authorize_params(client_id, challenge), "decision": "deny"})
    query = parse_qs(urlsplit(r.json()["redirect_to"]).query)
    assert query["error"] == ["access_denied"]
    assert query["state"] == ["xyz-state"]
    assert query["iss"] == [ORIGIN]
    assert "code" not in query


def test_decision_with_a_bad_redirect_uri_never_redirects(client):
    client_id = register(client)["client_id"]
    _, challenge = pkce()
    params = authorize_params(client_id, challenge, redirect_uri="https://chatgpt.com/elsewhere")
    r = client.post("/api/oauth/authorize", json={**params, "decision": "allow"})
    assert r.status_code == 400


# ── Tokens and MCP ──────────────────────────────────────────────────────────
def test_full_round_trip(client):
    client_id = register(client)["client_id"]
    verifier, challenge = pkce()
    code = get_code(client, client_id, challenge)

    # PKCE failure and a wrong redirect_uri are refused
    bad = exchange(client, client_id, code, pkce()[0])
    assert bad.status_code == 400 and bad.json()["error"] == "invalid_grant"
    bad = exchange(client, client_id, code, verifier, redirect_uri="https://chatgpt.com/connector/oauth/abc")
    assert bad.status_code == 400 and bad.json()["error"] == "invalid_grant"

    r = exchange(client, client_id, code, verifier)
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    tokens = r.json()
    assert tokens["token_type"] == "Bearer"
    assert tokens["expires_in"] == 3600
    assert tokens["scope"] == "mcp"

    init = rpc(client, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}}, tokens["access_token"])
    assert init.status_code == 200
    assert init.json()["result"]["serverInfo"]["name"] == "enchanted-spoon"
    assert init.json()["result"]["protocolVersion"] == "2025-06-18"

    note = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={**MCP_HEADERS, "Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert note.status_code == 202

    listed = rpc(client, "tools/list", token=tokens["access_token"]).json()["result"]["tools"]
    assert any(t["name"] == "list_recipes" for t in listed)

    called = rpc(client, "tools/call", {"name": "get_overview", "arguments": {}}, tokens["access_token"]).json()["result"]
    assert called["isError"] is False
    assert called["structuredContent"]["account"]["email"] == "u1@example.com"

    # The code can't be used twice, and replaying it revokes what it produced
    replay = exchange(client, client_id, code, verifier)
    assert replay.status_code == 400 and replay.json()["error"] == "invalid_grant"
    assert rpc(client, "tools/list", token=tokens["access_token"]).status_code == 401


def test_refresh_rotation(client):
    client_id, tokens = connect(client)
    r = client.post("/api/oauth/token", data={"grant_type": "refresh_token", "client_id": client_id, "refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200, r.text
    rotated = r.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]
    assert rpc(client, "ping", token=rotated["access_token"]).json()["result"] == {}

    # The old refresh token is dead; replaying it ends the whole connection
    old = client.post("/api/oauth/token", data={"grant_type": "refresh_token", "client_id": client_id, "refresh_token": tokens["refresh_token"]})
    assert old.status_code == 400 and old.json()["error"] == "invalid_grant"
    assert rpc(client, "ping", token=rotated["access_token"]).status_code == 401


def test_expired_access_token_is_refused_with_the_header(client, factory):
    _, tokens = connect(client)
    with factory() as session:
        for row in session.query(OAuthToken).filter(OAuthToken.kind == "access"):
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    r = rpc(client, "tools/list", token=tokens["access_token"])
    assert r.status_code == 401
    assert "resource_metadata=" in r.headers["www-authenticate"]
    assert 'error="invalid_token"' in r.headers["www-authenticate"]


def test_revoke(client):
    client_id, tokens = connect(client)
    r = client.post("/api/oauth/revoke", data={"client_id": client_id, "token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert rpc(client, "ping", token=tokens["access_token"]).status_code == 401
    # Unknown tokens are fine (RFC 7009)
    assert client.post("/api/oauth/revoke", data={"client_id": client_id, "token": "nope"}).status_code == 200


def test_confidential_client_authenticates(client):
    registered = register(client, "client_secret_basic")
    client_id, secret = registered["client_id"], registered["client_secret"]
    verifier, challenge = pkce()
    code = get_code(client, client_id, challenge)
    data = {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT, "code_verifier": verifier}

    wrong = client.post("/api/oauth/token", data=data, auth=(client_id, "wrong-secret"))
    assert wrong.status_code == 401 and wrong.json()["error"] == "invalid_client"
    missing = client.post("/api/oauth/token", data={**data, "client_id": client_id})
    assert missing.status_code == 401

    ok = client.post("/api/oauth/token", data=data, auth=(client_id, secret))
    assert ok.status_code == 200, ok.text
    # client_secret_post works too
    refreshed = client.post(
        "/api/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": ok.json()["refresh_token"], "client_id": client_id, "client_secret": secret},
    )
    assert refreshed.status_code == 200


def test_unknown_grant_type(client):
    client_id = register(client)["client_id"]
    r = client.post("/api/oauth/token", data={"grant_type": "password", "client_id": client_id})
    assert r.status_code == 400 and r.json()["error"] == "unsupported_grant_type"


def test_kill_switch(client, monkeypatch):
    _, tokens = connect(client)
    monkeypatch.setenv("MCP_ENABLED", "false")
    assert rpc(client, "ping", token=tokens["access_token"]).status_code == 404
    assert client.get("/.well-known/oauth-authorization-server").status_code == 404
    assert client.get("/.well-known/oauth-protected-resource").status_code == 404
    assert client.post("/api/oauth/register", json={"redirect_uris": [REDIRECT]}).status_code == 404


def test_connected_apps_and_disconnect(client):
    _, tokens = connect(client)
    listed = client.get("/api/oauth/connections").json()["connections"]
    assert [c["client_name"] for c in listed] == ["ChatGPT"]
    r = client.delete("/api/oauth/connections")
    assert r.json()["revoked"] >= 2
    assert client.get("/api/oauth/connections").json()["connections"] == []
    assert rpc(client, "ping", token=tokens["access_token"]).status_code == 401


def test_get_on_mcp_is_not_a_stream(client):
    _, tokens = connect(client)
    r = client.get("/api/mcp", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 405
