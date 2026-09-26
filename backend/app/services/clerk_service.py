"""app/services/clerk_service.py

Thin client for the Clerk Backend API (https://api.clerk.com), authenticated
with CLERK_SECRET_KEY. Used where a JWT claim alone isn't trustworthy enough:
confirming an email is verified before relinking an account to it, and
deleting the Clerk identity when a user deletes their account.
"""

import logging
from typing import Optional

import httpx

from ..core.auth_config import get_auth_settings

logger = logging.getLogger(__name__)

CLERK_API_BASE = "https://api.clerk.com/v1"
CLERK_API_TIMEOUT = 8.0


class ClerkApiError(Exception):
    """Raised when a Clerk Backend API call fails or Clerk isn't configured."""


def _secret_key() -> Optional[str]:
    return get_auth_settings().clerk_secret_key


def _headers(secret: str) -> dict:
    return {"Authorization": f"Bearer {secret}"}


def clerk_user_has_verified_email(clerk_id: str, email: str) -> bool:
    """
    Whether ``email`` is a *verified* address on the Clerk user ``clerk_id``.

    Fails closed: any configuration or network problem returns False, so an
    account is never relinked on an unconfirmed email.
    """
    secret = _secret_key()
    if not secret:
        logger.warning("CLERK_SECRET_KEY not set; cannot verify email for account relink")
        return False

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
