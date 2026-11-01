"""Account access policy for free, Pro, and grandfathered users.

Accounts created before ``LEGACY_FREE_CUTOFF`` (the coordinated release
instant, not a fixed calendar date) keep the full free plan until
``FREE_PLAN_SUNSET_AT`` in ``FREE_PLAN_SUNSET_TIMEZONE``. The sunset default
is March 31, 2027 at 11:59 PM America/New_York. After that instant those
accounts become view-only: they can still read and export, and they can
subscribe, but writes are rejected. Accounts created at or after the cutoff
stay on the metered free plan until trial onboarding ships. Until
``LEGACY_FREE_CUTOFF`` is set, nobody is in the legacy cohort.

The same instant is the end of the web-only FOUNDER30 offer.

Pro access (admin, Stripe, store subscription, or a manual grant) is
always full, including after the sunset.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

ACCESS_FULL = "full"
ACCESS_READ_ONLY = "read_only"

_DEFAULT_SUNSET_LOCAL = "2027-03-31T23:59:00"
_DEFAULT_SUNSET_TIMEZONE = "America/New_York"


class AccessPolicySettings(BaseSettings):
    """When the grandfathered free plan and FOUNDER30 both end.

    ``free_plan_sunset_at`` is a local civil time. When it has no offset,
    it is read in ``free_plan_sunset_timezone`` (default America/New_York).
    An offset in the value wins, so ``2027-04-01T03:59:00Z`` is the same
    instant as 11:59 PM Eastern on March 31, 2027.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    free_plan_sunset_at: str = _DEFAULT_SUNSET_LOCAL
    free_plan_sunset_timezone: str = _DEFAULT_SUNSET_TIMEZONE
    # ISO-8601 instant of the coordinated release. Empty until that deploy.
    # Accounts created strictly before it are the legacy free cohort.
    legacy_free_cutoff: str = ""


@lru_cache()
def get_access_policy_settings() -> AccessPolicySettings:
    """Load the sunset once per process."""
    return AccessPolicySettings()


def free_plan_sunset(settings: AccessPolicySettings | None = None) -> datetime:
    """The shared end of grandfathered free access and FOUNDER30."""
    settings = settings or get_access_policy_settings()
    parsed = datetime.fromisoformat(settings.free_plan_sunset_at)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(settings.free_plan_sunset_timezone))
    return parsed.astimezone(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Treat naive timestamps as UTC. SQLite returns them without tzinfo."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def legacy_free_cutoff(settings: AccessPolicySettings | None = None) -> datetime | None:
    """Release instant that splits legacy free accounts from newer ones.

    Unset means the release has not been recorded yet, so no account is
    grandfathered and none will be flipped to read-only by the sunset.
    """
    settings = settings or get_access_policy_settings()
    raw = settings.legacy_free_cutoff.strip()
    if not raw:
        return None
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def is_existing_free_cohort(
    created_at: datetime | None,
    settings: AccessPolicySettings | None = None,
) -> bool:
    """True when the account was created before the release cutoff."""
    cutoff = legacy_free_cutoff(settings)
    if cutoff is None or created_at is None:
        return False
    return as_utc(created_at) < cutoff


def at_or_before_plan_sunset(now: datetime, settings: AccessPolicySettings | None = None) -> bool:
    """True through the shared free-plan and FOUNDER30 end instant."""
    return as_utc(now) <= free_plan_sunset(settings)


def resolve_access_mode(
    *,
    is_admin: bool,
    has_pro_access: bool,
    created_at: datetime | None,
    now: datetime,
    settings: AccessPolicySettings | None = None,
) -> str:
    """Return ``full`` or ``read_only`` for an account at ``now``."""
    if is_admin or has_pro_access:
        return ACCESS_FULL
    if not is_existing_free_cohort(created_at, settings):
        return ACCESS_FULL
    if at_or_before_plan_sunset(now, settings):
        return ACCESS_FULL
    return ACCESS_READ_ONLY
