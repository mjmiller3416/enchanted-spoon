"""The Enchanted Spoon Alexa skill, end to end.

Covers what someone says ("a gallon of milk and two cans of beans") becoming
list items, Amazon's request-signature rules (with a throwaway CA standing in
for Amazon's), Alexa account linking through the OAuth server (Amazon
redirect URIs, the narrow ``alexa`` scope), and signed skill requests that
add to and read the shopping list.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from cryptography.x509.verification import Store
from fastapi.testclient import TestClient

from app.api.alexa import get_verifier
from app.api.auth import get_current_user
from app.database.db import get_session
from app.main import app
from app.models.shopping_item import ShoppingItem
from app.models.user import User
from app.services.alexa.verification import (
    AlexaVerificationError,
    SignatureVerifier,
    check_application,
    check_timestamp,
    validate_cert_url,
)
from app.utils.spoken_items import parse_spoken_items

ORIGIN = "https://es.test"
SKILL_ID = "amzn1.ask.skill.test-skill"
AMAZON_REDIRECT = "https://pitangui.amazon.com/api/skill/link/M2TESTVENDOR"
CHATGPT_REDIRECT = "https://chatgpt.com/connector_platform_oauth_redirect"
CERT_URL = "https://s3.amazonaws.com/echo.api/echo-api-cert-test.pem"


# ── What was said → items ───────────────────────────────────────────────────
def said(phrase: str, known: tuple[str, ...] = ()) -> list[tuple[str, float, Optional[str]]]:
    return [(i.name, i.quantity, i.unit) for i in parse_spoken_items(phrase, lambda n: n in known)]


@pytest.mark.parametrize(
    "phrase, expected",
    [
        ("milk", [("milk", 1.0, None)]),
        ("a gallon of milk", [("milk", 1.0, "gallon")]),
        ("a half gallon of milk", [("milk", 0.5, "gallon")]),
        ("half a gallon of milk", [("milk", 0.5, "gallon")]),
        ("two cans of black beans", [("black beans", 2.0, "can")]),
        ("3 pounds ground beef", [("ground beef", 3.0, "lb")]),
        ("one and a half pounds of chicken", [("chicken", 1.5, "lb")]),
        ("a dozen eggs", [("eggs", 1.0, "dozen")]),
        ("two avocados", [("avocados", 2.0, None)]),
        ("a couple of lemons", [("lemons", 2.0, None)]),
        ("some apples", [("apples", 1.0, None)]),
        ("two rolls", [("rolls", 2.0, None)]),
        ("a roll of paper towels", [("paper towels", 1.0, "roll")]),
        ("milk and eggs", [("milk", 1.0, None), ("eggs", 1.0, None)]),
        ("a gallon of milk and two loaves of bread", [("milk", 1.0, "gallon"), ("bread", 2.0, "loaf")]),
        ("milk to my shopping list", [("milk", 1.0, None)]),
        ("eggs on the grocery list please", [("eggs", 1.0, None)]),
        ("half and half", [("half and half", 1.0, None)]),
        ("a box of mac and cheese", [("mac and cheese", 1.0, "box")]),
        ("salt and pepper", [("salt", 1.0, None), ("pepper", 1.0, None)]),
        ("milk and milk", [("milk", 1.0, None)]),
        ("", []),
        ("a", []),
    ],
)
def test_parse_spoken_items(phrase, expected):
    assert said(phrase) == expected


def test_a_known_ingredient_with_and_stays_whole():
    assert said("chicken and dumplings", known=("chicken and dumplings",)) == [("chicken and dumplings", 1.0, None)]
    assert said("chicken and dumplings") == [("chicken", 1.0, None), ("dumplings", 1.0, None)]


# ── Request verification ────────────────────────────────────────────────────
def _name(cn: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


class FakeAmazon:
    """A root CA and an echo-api leaf it signed, like Amazon's chain."""

    def __init__(self, san: str = "echo-api.amazon.com", expired: bool = False) -> None:
        now = datetime.now(timezone.utc)
        self.root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.root = (
            x509.CertificateBuilder()
            .subject_name(_name("Test Root"))
            .issuer_name(_name("Test Root"))
            .public_key(self.root_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=30))
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self.root_key.public_key()), critical=False)
            .sign(self.root_key, hashes.SHA256())
        )
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        start, end = (now - timedelta(days=60), now - timedelta(days=1)) if expired else (now - timedelta(days=1), now + timedelta(days=90))
        self.leaf = (
            x509.CertificateBuilder()
            .subject_name(_name(san))
            .issuer_name(self.root.subject)
            .public_key(self.key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(start)
            .not_valid_after(end)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(san)]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(self.root_key.public_key()), critical=False
            )
            .sign(self.root_key, hashes.SHA256())
        )
        self.fetches = 0

    def pem(self) -> bytes:
        return self.leaf.public_bytes(serialization.Encoding.PEM)

    def fetch(self, url: str) -> bytes:
        self.fetches += 1
        return self.pem()

    def verifier(self) -> SignatureVerifier:
        store = Store([self.root])
        return SignatureVerifier(fetch=self.fetch, roots=lambda: store)

    def sign(self, body: bytes) -> str:
        return base64.b64encode(self.key.sign(body, padding.PKCS1v15(), hashes.SHA256())).decode()


@pytest.fixture(scope="module")
def amazon() -> FakeAmazon:
    return FakeAmazon()


@pytest.mark.parametrize(
    "url",
    [
        "https://s3.amazonaws.com/echo.api/echo-api-cert.pem",
        "https://s3.amazonaws.com:443/echo.api/echo-api-cert.pem",
        "HTTPS://S3.AMAZONAWS.COM/echo.api/echo-api-cert.pem",
        "https://s3.amazonaws.com/echo.api/../echo.api/echo-api-cert.pem",
    ],
)
def test_cert_urls_amazon_allows(url):
    validate_cert_url(url)


@pytest.mark.parametrize(
    "url",
    [
        None,
        "http://s3.amazonaws.com/echo.api/echo-api-cert.pem",
        "https://notamazon.com/echo.api/echo-api-cert.pem",
        "https://s3.amazonaws.com/EcHo.aPi/echo-api-cert.pem",
        "https://s3.amazonaws.com/invalid.path/echo-api-cert.pem",
        "https://s3.amazonaws.com:563/echo.api/echo-api-cert.pem",
        "https://s3.amazonaws.com/echo.api/../invalid.path/echo-api-cert.pem",
    ],
)
def test_cert_urls_amazon_refuses(url):
    with pytest.raises(AlexaVerificationError):
        validate_cert_url(url)


def test_signature_checks(amazon):
    verifier = amazon.verifier()
    body = b'{"hello": "alexa"}'
    verifier.verify(CERT_URL, amazon.sign(body), body)
    verifier.verify(CERT_URL, amazon.sign(body), body)
    assert amazon.fetches == 1  # the verified key is cached
    for bad_sig, bad_body in ((amazon.sign(body), b'{"hello": "evil"}'), ("not base64!", body), (None, body)):
        with pytest.raises(AlexaVerificationError):
            verifier.verify(CERT_URL, bad_sig, bad_body)


@pytest.mark.parametrize("kwargs", [{"san": "evil.example.com"}, {"expired": True}])
def test_untrusted_chains_are_refused(kwargs):
    fake = FakeAmazon(**kwargs)
    body = b"{}"
    with pytest.raises(AlexaVerificationError):
        fake.verifier().verify(CERT_URL, fake.sign(body), body)


def test_a_chain_from_an_unknown_root_is_refused(amazon):
    other = FakeAmazon()
    body = b"{}"
    verifier = SignatureVerifier(fetch=other.fetch, roots=lambda: Store([amazon.root]))
    with pytest.raises(AlexaVerificationError):
        verifier.verify(CERT_URL, other.sign(body), body)


def test_timestamp_window():
    now = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    check_timestamp("2026-11-15T12:02:00Z", now)
    check_timestamp("2026-11-15T11:58:00Z", now)
    for stale in ("2026-11-15T11:57:00Z", "2026-11-15T12:03:00Z", "yesterday", None):
        with pytest.raises(AlexaVerificationError):
            check_timestamp(stale, now)


def test_application_id():
    envelope = {"context": {"System": {"application": {"applicationId": SKILL_ID}}}}
    check_application(envelope, frozenset({SKILL_ID}))
    with pytest.raises(AlexaVerificationError):
        check_application(envelope, frozenset({"amzn1.ask.skill.other"}))


# ── The endpoint, with account linking ──────────────────────────────────────
@pytest.fixture()
def factory(file_db, monkeypatch, amazon):
    """User 1 signed in (admin), user 2 a second account; the skill configured; the fake Amazon trusted."""
    monkeypatch.setenv("MCP_PUBLIC_URL", ORIGIN)
    monkeypatch.setenv("ALEXA_SKILL_ID", SKILL_ID)
    monkeypatch.delenv("MCP_ENABLED", raising=False)
    monkeypatch.delenv("MCP_AUTHORIZE_URL", raising=False)
    with file_db() as session:
        session.get(User, 1).is_admin = True
        session.add(User(id=2, clerk_id="file_db_user_2", email="u2@example.com"))
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

    verifier = amazon.verifier()
    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = _signed_in
    app.dependency_overrides[get_verifier] = lambda: verifier
    yield file_db
    for dep in (get_session, get_current_user, get_verifier):
        app.dependency_overrides.pop(dep, None)


@pytest.fixture()
def client(factory) -> TestClient:
    return TestClient(app)


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def link_account(client: TestClient, redirect: str = AMAZON_REDIRECT, scope: str = "alexa") -> dict:
    """What Alexa account linking does: a pre-registered confidential client, consent, code + PKCE exchange."""
    reg = client.post(
        "/api/oauth/register",
        json={"redirect_uris": [redirect], "client_name": "Amazon Alexa", "token_endpoint_auth_method": "client_secret_basic"},
    )
    assert reg.status_code == 201, reg.text
    creds = reg.json()
    verifier, challenge = pkce()
    params = {
        "response_type": "code",
        "client_id": creds["client_id"],
        "redirect_uri": redirect,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "alexa-state",
        "scope": scope,
    }
    check = client.get("/api/oauth/authorize/check", params=params).json()
    assert check["status"] == "ok"
    decided = client.post("/api/oauth/authorize", json={**params, "decision": "allow"})
    code = parse_qs(urlsplit(decided.json()["redirect_to"]).query)["code"][0]
    basic = base64.b64encode(f"{creds['client_id']}:{creds['client_secret']}".encode()).decode()
    token = client.post(
        "/api/oauth/token",
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect, "code_verifier": verifier},
        headers={"Authorization": f"Basic {basic}"},
    )
    assert token.status_code == 200, token.text
    return {**token.json(), "consent_scope": check["scope"], "basic": basic}


def envelope(request: Dict[str, Any], token: Optional[str] = None, skill_id: str = SKILL_ID) -> Dict[str, Any]:
    user: Dict[str, Any] = {"userId": "amzn1.ask.account.TEST"}
    if token:
        user["accessToken"] = token
    request.setdefault("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    request.setdefault("requestId", "amzn1.echo-api.request.test")
    request.setdefault("locale", "en-US")
    return {
        "version": "1.0",
        "session": {"new": True, "sessionId": "s", "application": {"applicationId": skill_id}, "user": user},
        "context": {"System": {"application": {"applicationId": skill_id}, "user": user}},
        "request": request,
    }


def add_intent(item: Optional[str]) -> Dict[str, Any]:
    slots = {"item": {"name": "item", "value": item}} if item is not None else {"item": {"name": "item"}}
    return {"type": "IntentRequest", "intent": {"name": "AddItemIntent", "slots": slots}}


def send(client: TestClient, amazon: FakeAmazon, payload: Dict[str, Any], sign: bool = True):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "SignatureCertChainUrl": CERT_URL}
    if sign:
        headers["Signature-256"] = amazon.sign(body)
    return client.post("/api/alexa", content=body, headers=headers)


def speech(response) -> str:
    assert response.status_code == 200, response.text
    return response.json()["response"]["outputSpeech"]["text"]


def needed_items(factory, user_id: int = 1) -> dict[str, tuple[float, Optional[str]]]:
    with factory() as session:
        rows = session.query(ShoppingItem).filter_by(user_id=user_id, have=False).all()
        return {r.ingredient_name: (r.quantity, r.unit) for r in rows}


def test_registration_accepts_alexa_link_urls_only(client):
    for bad in (
        "https://pitangui.amazon.com/somewhere-else",
        "https://pitangui.amazon.com/api/skill/link/",
        "http://pitangui.amazon.com/api/skill/link/M2TESTVENDOR",
        "https://amazon.com.evil.test/api/skill/link/M2TESTVENDOR",
    ):
        r = client.post("/api/oauth/register", json={"redirect_uris": [bad]})
        assert r.status_code == 400, bad
    for good in (
        "https://layla.amazon.com/api/skill/link/M2TESTVENDOR",
        "https://alexa.amazon.co.jp/api/skill/link/M2TESTVENDOR",
        AMAZON_REDIRECT,
    ):
        assert client.post("/api/oauth/register", json={"redirect_uris": [good]}).status_code == 201


def test_alexa_links_with_the_narrow_scope_even_when_asking_for_more(client, amazon):
    linked = link_account(client, scope="mcp")
    assert linked["scope"] == "alexa"
    assert linked["consent_scope"] == "alexa"
    # The Alexa token can't drive the full ChatGPT connector...
    r = client.post(
        "/api/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        headers={"Authorization": f"Bearer {linked['access_token']}"},
    )
    assert r.status_code == 401
    # ...and a ChatGPT (mcp) token can't act as the skill.
    chatgpt = link_account(client, redirect=CHATGPT_REDIRECT, scope="mcp")
    assert chatgpt["scope"] == "mcp"
    reply = send(client, amazon, envelope(add_intent("milk"), chatgpt["access_token"]))
    assert reply.json()["response"]["card"] == {"type": "LinkAccount"}


def test_refreshed_alexa_tokens_keep_the_scope(client, amazon):
    linked = link_account(client)
    r = client.post(
        "/api/oauth/token",
        data={"grant_type": "refresh_token", "refresh_token": linked["refresh_token"]},
        headers={"Authorization": f"Basic {linked['basic']}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["scope"] == "alexa"
    assert speech(send(client, amazon, envelope(add_intent("milk"), r.json()["access_token"]))).startswith("Added milk")


def test_unlinked_gets_a_link_account_card(client, amazon):
    for request in ({"type": "LaunchRequest"}, add_intent("milk")):
        r = send(client, amazon, envelope(request))
        body = r.json()["response"]
        assert body["card"] == {"type": "LinkAccount"}
        assert "link your account" in body["outputSpeech"]["text"]
    r = send(client, amazon, envelope(add_intent("milk"), token="not-a-real-token"))
    assert r.json()["response"]["card"] == {"type": "LinkAccount"}


def test_add_items(client, amazon, factory):
    token = link_account(client)["access_token"]
    text = speech(send(client, amazon, envelope(add_intent("a gallon of milk"), token)))
    assert text == "Added a gallon of milk to your shopping list."
    assert needed_items(factory) == {"milk": (1.0, "gallon")}

    text = speech(send(client, amazon, envelope(add_intent("two cans of black beans and milk"), token)))
    assert text == "Added two cans of black beans to your shopping list. Milk is already on your list."
    assert needed_items(factory) == {"milk": (1.0, "gallon"), "black beans": (2.0, "can")}

    assert send(client, amazon, envelope(add_intent("a gallon of milk"), token)).json()["response"]["shouldEndSession"]


def test_read_the_list(client, amazon):
    token = link_account(client)["access_token"]
    assert speech(send(client, amazon, envelope({"type": "IntentRequest", "intent": {"name": "ReadListIntent"}}, token))) == (
        "Your shopping list is empty."
    )
    send(client, amazon, envelope(add_intent("milk and eggs"), token))
    text = speech(send(client, amazon, envelope({"type": "IntentRequest", "intent": {"name": "ReadListIntent"}}, token)))
    assert text == "You have 2 things on your shopping list: milk and eggs."


def test_empty_add_launch_help_and_stop(client, amazon):
    token = link_account(client)["access_token"]
    r = send(client, amazon, envelope(add_intent(None), token)).json()["response"]
    assert r["shouldEndSession"] is False and "What should I add" in r["outputSpeech"]["text"]
    r = send(client, amazon, envelope({"type": "LaunchRequest"}, token)).json()["response"]
    assert r["shouldEndSession"] is False
    r = send(client, amazon, envelope({"type": "IntentRequest", "intent": {"name": "AMAZON.HelpIntent"}})).json()["response"]
    assert r["shouldEndSession"] is False and "gallon of milk" in r["outputSpeech"]["text"]
    r = send(client, amazon, envelope({"type": "IntentRequest", "intent": {"name": "AMAZON.StopIntent"}})).json()["response"]
    assert r["shouldEndSession"] is True
    assert send(client, amazon, envelope({"type": "SessionEndedRequest", "reason": "USER_INITIATED"})).json() == {
        "version": "1.0",
        "response": {},
    }


def test_read_only_accounts_cannot_add(client, amazon, factory):
    token = link_account(client)["access_token"]
    with factory() as session:
        user = session.get(User, 1)
        user.is_admin = False
        user.read_only_at = datetime.now(timezone.utc)
        session.commit()
    text = speech(send(client, amazon, envelope(add_intent("milk"), token)))
    assert "read only" in text
    assert needed_items(factory) == {}


def test_requests_that_are_not_alexas_are_refused(client, amazon, factory):
    token = link_account(client)["access_token"]
    assert send(client, amazon, envelope(add_intent("milk"), token), sign=False).status_code == 400
    assert send(client, amazon, envelope(add_intent("milk"), token, skill_id="amzn1.ask.skill.other")).status_code == 400
    stale = add_intent("milk")
    stale["timestamp"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert send(client, amazon, envelope(stale, token)).status_code == 400
    # A body changed after signing
    payload = envelope(add_intent("milk"), token)
    body = json.dumps(payload).encode()
    tampered = body.replace(b"milk", b"beer")
    r = client.post(
        "/api/alexa",
        content=tampered,
        headers={"Content-Type": "application/json", "SignatureCertChainUrl": CERT_URL, "Signature-256": amazon.sign(body)},
    )
    assert r.status_code == 400
    assert needed_items(factory) == {}


def test_the_endpoint_is_off_without_a_skill_id(client, amazon, monkeypatch):
    monkeypatch.delenv("ALEXA_SKILL_ID")
    assert send(client, amazon, envelope({"type": "LaunchRequest"})).status_code == 404
