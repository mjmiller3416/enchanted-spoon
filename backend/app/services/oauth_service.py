"""app/services/oauth_service.py

The OAuth 2.1 authorization server behind the MCP connector (ChatGPT custom
connectors): dynamic client registration (RFC 7591), authorization codes
with PKCE S256, token issue and refresh rotation, revocation (RFC 7009), and
access-token checks for ``/api/mcp``.

Clients, codes and tokens are random url-safe strings of 32+ bytes, stored
only as SHA-256 digests. Each consent is a *grant*: the code and every token
it leads to share a ``grant_id``. Replaying a used code or a rotated refresh
token revokes the whole grant (the token may have leaked).

Errors are domain exceptions; the API layer (app/api/oauth.py) turns them
into RFC 6749 JSON, error pages or error redirects.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from ..core.mcp_config import (
    ACCESS_TOKEN_TTL,
    AUTHORIZATION_CODE_TTL,
    MCP_SCOPE,
    REFRESH_TOKEN_TTL,
    resource_url,
)
from ..models.oauth import OAuthAuthorizationCode, OAuthClient, OAuthToken
from ..repositories.oauth_repo import OAuthRepo

logger = logging.getLogger(__name__)

AUTH_METHODS = ("none", "client_secret_post", "client_secret_basic")
SUPPORTED_GRANTS = ("authorization_code", "refresh_token")
ALLOWED_REDIRECT_HOSTS = ("chatgpt.com", "chat.openai.com")
LOCAL_REDIRECT_HOSTS = ("localhost", "127.0.0.1")
_CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{43,128}$")
_VERIFIER_RE = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
MAX_REDIRECT_URIS = 10


# ── Domain exceptions ───────────────────────────────────────────────────────
class OAuthError(Exception):
    """An RFC 6749 error for the token, registration and revocation endpoints.

    Attributes:
        error: The RFC error code (``invalid_grant``, ``invalid_client``...).
        description: A plain sentence for ``error_description``.
        status_code: 400, or 401 for client authentication failures.
    """

    def __init__(self, error: str, description: str, status_code: int = 400) -> None:
        super().__init__(description)
        self.error = error
        self.description = description
        self.status_code = status_code


class AuthorizeRequestError(Exception):
    """The authorize request can't be trusted to redirect (unknown client, unregistered redirect URI).

    The API shows the message on an error page and never redirects.
    """


class AuthorizeRedirectError(Exception):
    """An authorize error that goes back to the client's redirect URI (``error``, ``state``, ``iss``)."""

    def __init__(self, error: str, description: str, redirect_uri: str, state: Optional[str]) -> None:
        super().__init__(description)
        self.error = error
        self.description = description
        self.redirect_uri = redirect_uri
        self.state = state


# ── Value objects ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AuthorizeRequest:
    """A validated authorization request, ready for consent."""

    client_id: str
    client_name: str
    redirect_uri: str
    code_challenge: str
    state: Optional[str]
    scope: str
    resource: Optional[str]


@dataclass(frozen=True)
class TokenPair:
    """What the token endpoint returns."""

    access_token: str
    refresh_token: str
    expires_in: int
    scope: str


@dataclass(frozen=True)
class RegisteredClient:
    """A new client and, for confidential clients, its one-time-visible secret."""

    client: OAuthClient
    client_secret: Optional[str]


@dataclass(frozen=True)
class Connection:
    """One live connection (grant) a user has made, for Settings."""

    client_name: str
    connected_at: datetime


# ── Helpers ─────────────────────────────────────────────────────────────────
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    """SQLite hands datetimes back naive; they were stored as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def digest(value: str) -> str:
    """SHA-256 hex digest of a secret, the only form secrets are stored in."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_secret() -> str:
    return secrets.token_urlsafe(32)


def pkce_s256(verifier: str) -> str:
    """BASE64URL(SHA256(verifier)) without padding (RFC 7636)."""
    raw = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def resource_matches(value: Optional[str]) -> bool:
    """Whether a ``resource`` parameter names this MCP server (a trailing slash is tolerated)."""
    if value is None or value == "":
        return True
    return value.rstrip("/") == resource_url().rstrip("/")


def redirect_uri_allowed(uri: str) -> bool:
    """ChatGPT's https callbacks, or http://localhost / 127.0.0.1 on any port for local tests."""
    try:
        parts = urlsplit(uri)
    except ValueError:
        return False
    if parts.fragment or not parts.hostname:
        return False
    host = parts.hostname.lower()
    if parts.scheme == "https" and host in ALLOWED_REDIRECT_HOSTS:
        return True
    return parts.scheme == "http" and host in LOCAL_REDIRECT_HOSTS


class OAuthService:
    """OAuth 2.1 authorization server logic. Commits its own changes."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = OAuthRepo(session)

    # ── Registration ────────────────────────────────────────────────────────
    def register_client(
        self,
        redirect_uris: object,
        client_name: Optional[str] = None,
        token_endpoint_auth_method: Optional[str] = None,
        grant_types: Optional[object] = None,
    ) -> RegisteredClient:
        """Register a client (RFC 7591). Clients never expire.

        Raises:
            OAuthError: ``invalid_redirect_uri`` or ``invalid_client_metadata``.
        """
        if not isinstance(redirect_uris, list) or not redirect_uris:
            raise OAuthError("invalid_redirect_uri", "redirect_uris must be a non-empty list.")
        if len(redirect_uris) > MAX_REDIRECT_URIS:
            raise OAuthError("invalid_redirect_uri", "Too many redirect_uris.")
        for uri in redirect_uris:
            if not isinstance(uri, str) or len(uri) > 2048 or not redirect_uri_allowed(uri):
                raise OAuthError(
                    "invalid_redirect_uri",
                    "Redirect URIs must be https on chatgpt.com or chat.openai.com "
                    "(or http://localhost for local testing).",
                )
        method = token_endpoint_auth_method or "client_secret_basic"
        if method not in AUTH_METHODS:
            raise OAuthError("invalid_client_metadata", f"Unsupported token_endpoint_auth_method: {method}.")
        grants = grant_types if grant_types is not None else ["authorization_code", "refresh_token"]
        if not isinstance(grants, list) or not all(isinstance(g, str) for g in grants):
            raise OAuthError("invalid_client_metadata", "grant_types must be a list of strings.")
        unsupported = [g for g in grants if g not in SUPPORTED_GRANTS]
        if unsupported:
            raise OAuthError("invalid_client_metadata", f"Unsupported grant_types: {', '.join(unsupported)}.")
        name = client_name.strip()[:255] if isinstance(client_name, str) and client_name.strip() else None

        secret = None if method == "none" else _new_secret()
        client = OAuthClient(
            client_id=_new_secret(),
            client_secret_hash=digest(secret) if secret else None,
            client_name=name,
            redirect_uris=json.dumps(redirect_uris),
            grant_types=json.dumps(grants),
            token_endpoint_auth_method=method,
        )
        self.repo.add_client(client)
        self.session.commit()
        logger.info("OAuth client registered (auth method %s)", method)
        return RegisteredClient(client=client, client_secret=secret)

    def delete_client(self, client_id: str) -> bool:
        """Remove a client registration (used to clean up test registrations). True if it existed."""
        client = self.repo.get_client(client_id)
        if client is None:
            return False
        self.repo.delete_client(client)
        self.session.commit()
        return True

    # ── Authorization ───────────────────────────────────────────────────────
    def validate_authorize_request(
        self,
        *,
        response_type: Optional[str],
        client_id: Optional[str],
        redirect_uri: Optional[str],
        code_challenge: Optional[str],
        code_challenge_method: Optional[str],
        state: Optional[str],
        scope: Optional[str],
        resource: Optional[str],
    ) -> AuthorizeRequest:
        """Check an authorization request before showing consent or issuing a code.

        Raises:
            AuthorizeRequestError: Unknown client or a redirect URI it didn't register (no redirect).
            AuthorizeRedirectError: Anything else wrong (sent back to the client).
        """
        client = self.repo.get_client(client_id) if client_id else None
        if client is None:
            raise AuthorizeRequestError("This app isn't registered with Enchanted Spoon. Try connecting again.")
        if not redirect_uri or redirect_uri not in json.loads(client.redirect_uris):
            raise AuthorizeRequestError("The return address in this request doesn't match the app's registration.")

        def fail(error: str, description: str) -> AuthorizeRedirectError:
            return AuthorizeRedirectError(error, description, redirect_uri, state)

        if response_type != "code":
            raise fail("unsupported_response_type", "Only response_type=code is supported.")
        if not code_challenge or not _CHALLENGE_RE.match(code_challenge):
            raise fail("invalid_request", "A PKCE code_challenge is required.")
        if code_challenge_method != "S256":
            raise fail("invalid_request", "code_challenge_method must be S256.")
        if not resource_matches(resource):
            raise fail("invalid_target", "Unknown resource.")
        # Only "mcp" exists; an empty scope means it, unknown scopes are ignored.
        return AuthorizeRequest(
            client_id=client.client_id,
            client_name=client.client_name or "An app",
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            state=state,
            scope=MCP_SCOPE,
            resource=resource.rstrip("/") if resource else None,
        )

    def issue_code(self, request: AuthorizeRequest, user_id: int) -> str:
        """Issue a single-use, 10-minute authorization code for a consented request."""
        code = _new_secret()
        self.repo.add_code(
            OAuthAuthorizationCode(
                code_hash=digest(code),
                client_id=request.client_id,
                user_id=user_id,
                grant_id=_new_secret(),
                redirect_uri=request.redirect_uri,
                code_challenge=request.code_challenge,
                scope=request.scope,
                resource=request.resource,
                expires_at=_now() + timedelta(seconds=AUTHORIZATION_CODE_TTL),
            )
        )
        self.session.commit()
        logger.info("OAuth authorization code issued for user %s", user_id)
        return code

    # ── Client authentication ───────────────────────────────────────────────
    def authenticate_client(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
    ) -> OAuthClient:
        """Authenticate the client at the token or revocation endpoint per its registered method.

        Public clients (``none``) need only their client_id. Confidential
        clients must present their secret, by Basic auth or in the form body
        (either is accepted whichever they registered; the secret is what counts),
        compared in constant time.

        Raises:
            OAuthError: ``invalid_client`` (401).
        """
        client = self.repo.get_client(client_id) if client_id else None
        if client is None:
            raise OAuthError("invalid_client", "Unknown client.", 401)
        method = client.token_endpoint_auth_method
        if method == "none":
            return client
        if client_secret is None or client.client_secret_hash is None:
            raise OAuthError("invalid_client", "Client authentication is required.", 401)
        if not hmac.compare_digest(digest(client_secret), client.client_secret_hash):
            raise OAuthError("invalid_client", "Client authentication failed.", 401)
        return client

    # ── Tokens ──────────────────────────────────────────────────────────────
    def _issue_pair(self, *, grant_id: str, client_id: str, user_id: int, scope: str, resource: Optional[str]) -> TokenPair:
        now = _now()
        access, refresh = _new_secret(), _new_secret()
        for value, kind, ttl in ((access, "access", ACCESS_TOKEN_TTL), (refresh, "refresh", REFRESH_TOKEN_TTL)):
            self.repo.add_token(
                OAuthToken(
                    token_hash=digest(value),
                    kind=kind,
                    grant_id=grant_id,
                    client_id=client_id,
                    user_id=user_id,
                    scope=scope,
                    resource=resource,
                    expires_at=now + timedelta(seconds=ttl),
                )
            )
        return TokenPair(access_token=access, refresh_token=refresh, expires_in=ACCESS_TOKEN_TTL, scope=scope)

    def exchange_code(
        self,
        client: OAuthClient,
        *,
        code: Optional[str],
        redirect_uri: Optional[str],
        code_verifier: Optional[str],
        resource: Optional[str],
    ) -> TokenPair:
        """Trade an authorization code for tokens.

        Raises:
            OAuthError: ``invalid_request``, ``invalid_grant`` or ``invalid_target``.
        """
        if not code or not code_verifier:
            raise OAuthError("invalid_request", "code and code_verifier are required.")
        row = self.repo.get_code(digest(code), for_update=True)
        if row is None:
            raise OAuthError("invalid_grant", "The authorization code is invalid.")
        now = _now()
        if row.used_at is not None:
            # A replayed code: revoke whatever it already produced.
            revoked = self.repo.revoke_grant(row.grant_id, now)
            self.session.commit()
            logger.warning("OAuth code reuse detected; revoked %s token(s)", revoked)
            raise OAuthError("invalid_grant", "The authorization code was already used.")
        if row.client_id != client.client_id:
            raise OAuthError("invalid_grant", "The authorization code was issued to another client.")
        if _aware(row.expires_at) <= now:
            raise OAuthError("invalid_grant", "The authorization code has expired.")
        if redirect_uri != row.redirect_uri:
            raise OAuthError("invalid_grant", "redirect_uri doesn't match the authorization request.")
        if not _VERIFIER_RE.match(code_verifier) or not hmac.compare_digest(
            pkce_s256(code_verifier), row.code_challenge
        ):
            raise OAuthError("invalid_grant", "PKCE verification failed.")
        if resource and not resource_matches(resource):
            raise OAuthError("invalid_target", "Unknown resource.")
        if not self.repo.mark_code_used(row.id, now):
            self.session.rollback()
            raise OAuthError("invalid_grant", "The authorization code was already used.")
        pair = self._issue_pair(
            grant_id=row.grant_id,
            client_id=row.client_id,
            user_id=row.user_id,
            scope=row.scope,
            resource=row.resource or (resource.rstrip("/") if resource else None),
        )
        self.session.commit()
        logger.info("OAuth tokens issued for user %s", row.user_id)
        return pair

    def refresh(self, client: OAuthClient, *, refresh_token: Optional[str], resource: Optional[str]) -> TokenPair:
        """Rotate a refresh token: the old one stops working and a new pair is issued.

        Raises:
            OAuthError: ``invalid_request``, ``invalid_grant`` or ``invalid_target``.
        """
        if not refresh_token:
            raise OAuthError("invalid_request", "refresh_token is required.")
        row = self.repo.get_token(digest(refresh_token), for_update=True)
        if row is None or row.kind != "refresh":
            raise OAuthError("invalid_grant", "The refresh token is invalid.")
        now = _now()
        if row.revoked_at is not None:
            # A rotated (or revoked) refresh token came back: treat the grant as leaked.
            self.repo.revoke_grant(row.grant_id, now)
            self.session.commit()
            raise OAuthError("invalid_grant", "The refresh token is no longer valid.")
        if row.client_id != client.client_id:
            raise OAuthError("invalid_grant", "The refresh token was issued to another client.")
        if _aware(row.expires_at) <= now:
            raise OAuthError("invalid_grant", "The refresh token has expired.")
        if resource and not resource_matches(resource):
            raise OAuthError("invalid_target", "Unknown resource.")
        if not self.repo.revoke_token(row.id, now):
            self.session.rollback()
            raise OAuthError("invalid_grant", "The refresh token is no longer valid.")
        pair = self._issue_pair(
            grant_id=row.grant_id, client_id=row.client_id, user_id=row.user_id, scope=row.scope, resource=row.resource
        )
        self.session.commit()
        return pair

    def revoke(self, client: OAuthClient, token: Optional[str]) -> None:
        """Revoke a token (RFC 7009). Revoking either token ends the whole connection.

        Unknown tokens, or another client's, are silently ignored (the RFC's 200).
        """
        if not token:
            return
        row = self.repo.get_token(digest(token))
        if row is None or row.client_id != client.client_id:
            return
        self.repo.revoke_grant(row.grant_id, _now())
        self.session.commit()

    def user_for_access_token(self, token: str) -> Optional[int]:
        """The user an MCP request acts as, or None if the token is unknown, expired or revoked."""
        row = self.repo.get_token(digest(token))
        if row is None or row.kind != "access" or row.revoked_at is not None:
            return None
        if _aware(row.expires_at) <= _now():
            return None
        return row.user_id

    # ── Connections (Settings) ──────────────────────────────────────────────
    def list_connections(self, user_id: int) -> List[Connection]:
        """A user's live connections, newest first (one per grant)."""
        tokens = self.repo.live_refresh_tokens(user_id, _now())
        names = {c.client_id: c.client_name for c in self.repo.get_clients(list({t.client_id for t in tokens}))}
        seen: set[str] = set()
        connections: List[Connection] = []
        for token in tokens:
            if token.grant_id in seen:
                continue
            seen.add(token.grant_id)
            connections.append(
                Connection(client_name=names.get(token.client_id) or "An app", connected_at=_aware(token.created_at))
            )
        return connections

    def disconnect_all(self, user_id: int) -> int:
        """Revoke every token the user has granted; returns how many were live."""
        count = self.repo.revoke_user_tokens(user_id, _now())
        self.session.commit()
        logger.info("Revoked %s OAuth token(s) for user %s", count, user_id)
        return count
