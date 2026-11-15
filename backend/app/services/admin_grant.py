"""Grant ``is_admin`` from the ``ADMIN_EMAILS`` environment variable.

The allowlist matches Clerk's verified primary email only, the same address
``ADMIN_EXEMPT_EMAILS`` uses. ``users.email`` and the JWT email claim are not
proof. Comparison is case-insensitive, and surrounding whitespace is ignored.
This only sets ``is_admin`` to true. An unset, empty, or blank value leaves
every user unchanged and does not call Clerk. A failed lookup, an unverified
primary, or an address that is not listed keeps the current flag.
"""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.user import User
from .clerk_service import cached_verified_primary_email

# Pre-provisioned rows use this clerk id until a real Clerk user claims them.
_UNCONFIRMED_CLERK_ID = "pending_claim"


def configured_admin_emails() -> set[str]:
    """Emails in ``ADMIN_EMAILS``.

    Commas split the value, surrounding spaces are trimmed, and case is
    ignored. A missing, empty, or whitespace-only value returns an empty set.
    """
    raw = os.environ.get("ADMIN_EMAILS")
    if raw is None or not raw.strip():
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _confirmable_clerk_id(user: User) -> str | None:
    """Clerk id that can be looked up, or None when the row cannot be confirmed."""
    clerk_id = (user.clerk_id or "").strip()
    if not clerk_id or clerk_id == _UNCONFIRMED_CLERK_ID:
        return None
    return clerk_id


def grant_admin_if_listed(user: User) -> bool:
    """Set ``is_admin`` when Clerk's verified primary email is listed.

    Returns True only when the flag changes from false to true. Already-admin
    users stay admin. A missing Clerk user, an unverified primary, a secondary
    address, and a failed lookup do not grant.
    """
    emails = configured_admin_emails()
    if not emails or user.is_admin:
        return False
    clerk_id = _confirmable_clerk_id(user)
    if clerk_id is None:
        return False
    verified = cached_verified_primary_email(clerk_id)
    if not verified or verified not in emails:
        return False
    user.is_admin = True
    return True


def grant_admins_from_env(session: Session) -> int:
    """Grant ``is_admin`` where Clerk confirms a listed verified primary email.

    Returns how many accounts changed. When ``ADMIN_EMAILS`` is missing,
    empty, or blank, this returns 0 without reading users or calling Clerk.
    Each non-admin account is checked by ``clerk_id``. The stored email is
    not the allowlist. Running it again is a no-op for anyone already admin.

    The caller commits. This flushes only when a flag changes.
    """
    if not configured_admin_emails():
        return 0
    rows = session.scalars(select(User).where(User.is_admin.is_(False))).all()
    changed = 0
    for user in rows:
        if grant_admin_if_listed(user):
            changed += 1
    if changed:
        session.flush()
    return changed
