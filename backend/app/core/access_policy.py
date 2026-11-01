"""Account access policy for free, Pro, and grandfathered users.

Existing free accounts — created on or before October 31, 2026 — keep the
full free plan through March 31, 2027. After that instant they become
view-only: they can still read and export, and they can subscribe, but
writes are rejected. Accounts created later stay on the current metered
free plan; the post-trial read-only funnel for new signups is separate
and not applied here.

Pro access (admin, Stripe, store subscription, or a manual grant) is
always full, including after the grandfather date.
"""

from __future__ import annotations

from datetime import datetime, timezone

# End of the day these rules were finalized (UTC).
EXISTING_FREE_CREATED_THROUGH = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)

# Last instant an existing free account still has the full free plan.
EXISTING_FREE_FULL_ACCESS_UNTIL = datetime(2027, 3, 31, 23, 59, 59, tzinfo=timezone.utc)

ACCESS_FULL = "full"
ACCESS_READ_ONLY = "read_only"


def as_utc(value: datetime) -> datetime:
    """Treat naive timestamps as UTC. SQLite returns them without tzinfo."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_existing_free_cohort(created_at: datetime | None) -> bool:
    """True when the account was created in the grandfathered cohort."""
    if created_at is None:
        return False
    return as_utc(created_at) <= EXISTING_FREE_CREATED_THROUGH


def resolve_access_mode(
    *,
    is_admin: bool,
    has_pro_access: bool,
    created_at: datetime | None,
    now: datetime,
) -> str:
    """Return ``full`` or ``read_only`` for an account at ``now``."""
    if is_admin or has_pro_access:
        return ACCESS_FULL
    if not is_existing_free_cohort(created_at):
        return ACCESS_FULL
    if as_utc(now) <= EXISTING_FREE_FULL_ACCESS_UNTIL:
        return ACCESS_FULL
    return ACCESS_READ_ONLY
