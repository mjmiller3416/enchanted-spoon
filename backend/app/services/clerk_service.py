"""app/services/clerk_service.py

Thin client for the Clerk Backend API (https://api.clerk.com), authenticated
with CLERK_SECRET_KEY. Used where a JWT claim alone isn't trustworthy enough:
confirming an email is verified before relinking an account to it, and
deleting the Clerk identity when a user deletes their account.
"""

import logging
import re
import threading
import time
from typing import Optional

import httpx

from ..core.auth_config import get_auth_settings

logger = logging.getLogger(__name__)

CLERK_API_BASE = "https://api.clerk.com/v1"
CLERK_API_TIMEOUT = 8.0
VERIFIED_EMAIL_TTL_SECONDS = 300

_verified_email_cache: dict[str, tuple[float, Optional[str]]] = {}
_verified_email_lock = threading.Lock()


class ClerkApiError(Exception):
    """Raised when a Clerk Backend API call fails or Clerk isn't configured."""


def _secret_key() -> Optional[str]:
    return get_auth_settings().clerk_secret_key


def _headers(secret: str) -> dict:
    return {"Authorization": f"Bearer {secret}"}


def fetch_clerk_user(clerk_id: str) -> Optional[dict]:
    """Clerk Backend API user, or None when the lookup cannot be trusted.

    Fails closed: a missing key, a network error, or a non-200 response
    returns None so an allowlist cannot match an unverified claim.
    """
    secret = _secret_key()
    if not secret or not clerk_id:
        logger.warning("CLERK_SECRET_KEY not set; cannot confirm a verified primary email")
        return None
    try:
        resp = httpx.get(
            f"{CLERK_API_BASE}/users/{clerk_id}",
            headers=_headers(secret),
            timeout=CLERK_API_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        logger.exception("Clerk user lookup failed for %s", clerk_id)
        return None
    return data if isinstance(data, dict) else None


def verified_primary_email(clerk_user: Optional[dict]) -> Optional[str]:
    """The primary email only when Clerk marks that address verified.

    Secondary addresses never match, even when they are verified. An
    unverified primary does not match. The comparison value is trimmed
    and lowercased.
    """
    if not isinstance(clerk_user, dict):
        return None
    primary_id = clerk_user.get("primary_email_address_id")
    if not isinstance(primary_id, str) or not primary_id:
        return None
    for address in clerk_user.get("email_addresses") or []:
        if not isinstance(address, dict) or address.get("id") != primary_id:
            continue
        verification = address.get("verification") or {}
        if not isinstance(verification, dict) or verification.get("status") != "verified":
            return None
        email = address.get("email_address")
        if isinstance(email, str) and email.strip():
            return email.strip().lower()
        return None
    return None


def clear_verified_email_cache() -> None:
    """Drop the in-process Clerk email cache. Tests use this."""
    with _verified_email_lock:
        _verified_email_cache.clear()


def cached_verified_primary_email(clerk_id: str, now: float | None = None) -> Optional[str]:
    """Verified primary email for ``clerk_id``, reused for about five minutes.

    A miss, an unverified primary, and a failed lookup are cached too, so
    ``ADMIN_EXEMPT_EMAILS`` does not call Clerk on every request. ``now`` is
    a monotonic timestamp for tests.
    """
    moment = time.monotonic() if now is None else now
    with _verified_email_lock:
        cached = _verified_email_cache.get(clerk_id)
        if cached is not None and moment - cached[0] < VERIFIED_EMAIL_TTL_SECONDS:
            return cached[1]
    email = verified_primary_email(fetch_clerk_user(clerk_id))
    with _verified_email_lock:
        _verified_email_cache[clerk_id] = (moment, email)
        expired = [
            key
            for key, (stored_at, _email) in _verified_email_cache.items()
            if moment - stored_at >= VERIFIED_EMAIL_TTL_SECONDS
        ]
        for key in expired:
            _verified_email_cache.pop(key, None)
        _verified_email_cache[clerk_id] = (moment, email)
    return email


def clerk_user_has_verified_email(clerk_id: str, email: str) -> bool:
    """
    Whether ``email`` is a *verified* address on the Clerk user ``clerk_id``.

    Fails closed: any configuration or network problem returns False, so an
    account is never relinked on an unconfirmed email.
    """
    data = fetch_clerk_user(clerk_id)
    if not data:
        return False

    wanted = email.strip().lower()
    for address in data.get("email_addresses") or []:
        if (address.get("email_address") or "").strip().lower() != wanted:
            continue
        verification = address.get("verification") or {}
        if verification.get("status") == "verified":
            return True
    return False


def delete_clerk_user(clerk_id: str) -> None:
    """
    Delete a user from Clerk. A user Clerk no longer has counts as deleted.

    Raises:
        ClerkApiError: Clerk isn't configured or the call failed.
    """
    secret = _secret_key()
    if not secret:
        raise ClerkApiError("CLERK_SECRET_KEY is not configured")

    try:
        resp = httpx.delete(
            f"{CLERK_API_BASE}/users/{clerk_id}",
            headers=_headers(secret),
            timeout=CLERK_API_TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise ClerkApiError("Could not reach Clerk") from e

    if resp.status_code == 404:
        return
    if resp.status_code >= 400:
        logger.error("Clerk user delete failed (%s): %s", resp.status_code, resp.text[:500])
        raise ClerkApiError(f"Clerk returned {resp.status_code}")


# Long enough for the WebView to redeem it, short enough that a leaked
# response is useless almost immediately.
SIGN_IN_TOKEN_TTL_SECONDS = 60
_USER_ID = re.compile(r"^user_[A-Za-z0-9]+$")
_SESSION_ID = re.compile(r"^sess_[A-Za-z0-9]+$")


def create_sign_in_token(user_id: str, expires_in_seconds: int = SIGN_IN_TOKEN_TTL_SECONDS) -> str:
    """Mint a Clerk sign-in token for ``user_id``.

    The returned string is the ticket itself. Callers must not log it.
    The Backend API response also carries a URL that embeds the ticket;
    that body is never logged or returned.

    Raises:
        ClerkApiError: Clerk isn't configured or the call failed.
    """
    secret = _secret_key()
    if not secret:
        raise ClerkApiError("CLERK_SECRET_KEY is not configured")
    if not _USER_ID.fullmatch(user_id):
        raise ClerkApiError("Clerk user id was not accepted")
    if not 1 <= expires_in_seconds <= 120:
        raise ClerkApiError("Sign-in token lifetime was not accepted")

    try:
        resp = httpx.post(
            f"{CLERK_API_BASE}/sign_in_tokens",
            headers=_headers(secret),
            json={"user_id": user_id, "expires_in_seconds": expires_in_seconds},
            timeout=CLERK_API_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise ClerkApiError("Could not reach Clerk") from exc

    if resp.status_code >= 400:
        logger.error("Clerk sign-in token was not created (%s)", resp.status_code)
        raise ClerkApiError(f"Clerk returned {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise ClerkApiError("Could not reach Clerk") from exc

    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or not token or len(token) > 4000:
        logger.error("Clerk sign-in token response did not include a ticket")
        raise ClerkApiError("Clerk returned an incomplete sign-in token")
    return token


def revoke_clerk_session(session_id: str) -> None:
    """End a Clerk session. A session Clerk no longer has counts as revoked.

    Raises:
        ClerkApiError: Clerk isn't configured or the call failed.
    """
    secret = _secret_key()
    if not secret:
        raise ClerkApiError("CLERK_SECRET_KEY is not configured")
    if not _SESSION_ID.fullmatch(session_id):
        raise ClerkApiError("Clerk session id was not accepted")

    try:
        resp = httpx.delete(
            f"{CLERK_API_BASE}/sessions/{session_id}",
            headers=_headers(secret),
            timeout=CLERK_API_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise ClerkApiError("Could not reach Clerk") from exc

    if resp.status_code in (200, 202, 204, 404):
        return
    logger.error("Clerk session revoke failed (%s)", resp.status_code)
    raise ClerkApiError(f"Clerk returned {resp.status_code}")


def issue_browser_sign_in_ticket(user_id: str, session_id: str) -> str:
    """Create a short-lived sign-in token, then revoke the native session.

    Revocation is best-effort. The ticket does not depend on that session
    staying active, and a failed revoke must not hide a ticket we already
    minted. The native session JWT expires on its own within about a minute.
    """
    ticket = create_sign_in_token(user_id)
    try:
        revoke_clerk_session(session_id)
    except ClerkApiError:
        logger.warning("Native Clerk session was not revoked")
    return ticket
