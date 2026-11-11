"""Grant ``is_admin`` from the ``ADMIN_EMAILS`` environment variable.

The match is the email stored on the user row. Comparison is
case-insensitive, and surrounding whitespace is ignored. This only sets
``is_admin`` to true. An unset, empty, or blank value leaves every user
unchanged, and an address that is not listed keeps its current flag.
"""

from __future__ import annotations

import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.user import User


def configured_admin_emails() -> set[str]:
    """Emails in ``ADMIN_EMAILS``.

    Commas split the value, surrounding spaces are trimmed, and case is
    ignored. A missing, empty, or whitespace-only value returns an empty set.
    """
    raw = os.environ.get("ADMIN_EMAILS")
    if raw is None or not raw.strip():
        return set()
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def grant_admin_if_listed(user: User) -> bool:
    """Set ``is_admin`` when this user's stored email is listed.

    Returns True only when the flag changes from false to true. Already-admin
    users, and users whose email is not listed, are left as they are.
    """
    emails = configured_admin_emails()
    if not emails or user.is_admin:
        return False
    email = (user.email or "").strip().lower()
    if not email or email not in emails:
        return False
    user.is_admin = True
    return True


def grant_admins_from_env(session: Session) -> int:
    """Grant ``is_admin`` to every stored user listed in ``ADMIN_EMAILS``.

    Returns how many accounts changed. When the variable is missing, empty,
    or blank, this returns 0 without reading or writing users. Running it
    again is a no-op for anyone who is already admin.

    The caller commits. This flushes only when a flag changes.
    """
    emails = configured_admin_emails()
    if not emails:
        return 0
    rows = session.scalars(
        select(User).where(func.lower(func.trim(User.email)).in_(sorted(emails)))
    ).all()
    changed = 0
    for user in rows:
        if grant_admin_if_listed(user):
            changed += 1
    if changed:
        session.flush()
    return changed
