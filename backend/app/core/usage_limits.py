"""app/core/usage_limits.py

Usage caps for Gemini-backed AI features.

Launch accounts use the approved cost-control caps. Accounts persisted as
`usage_plan=legacy` (see the soft-launch migration) keep their previous
allowances. Trial caps cover the whole trial, not a calendar month. Expired
and read-only accounts are capped at zero. Accounts created on or after
``LEGACY_FREE_CUTOFF`` use the ``none`` tier (also zero). Unknown tiers fall
back to free.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from app.models.user import User

# Launch caps. Pro: 20 images / 300 chats / 200 suggestions / 50 imports.
# Trial caps span the whole trial. One image is one generated photo.
# Suggestions are shared by meal ideas, nutrition, recipe generation, and tips.
TIER_USAGE_LIMITS: dict[str, dict[str, int]] = {
    "pro": {
        "ai_images_generated": 20,
        "ai_suggestions_requested": 200,
        "ai_assistant_messages": 300,
        "recipes_imported": 50,
    },
    "trial": {
        "ai_images_generated": 3,
        "ai_suggestions_requested": 20,
        "ai_assistant_messages": 25,
        "recipes_imported": 5,
    },
    "expired": {
        "ai_images_generated": 0,
        "ai_suggestions_requested": 0,
        "ai_assistant_messages": 0,
        "recipes_imported": 0,
    },
    # Accounts created on or after LEGACY_FREE_CUTOFF. No monthly free AI.
    "none": {
        "ai_images_generated": 0,
        "ai_suggestions_requested": 0,
        "ai_assistant_messages": 0,
        "recipes_imported": 0,
    },
    "free": {
        "ai_images_generated": 3,
        "ai_suggestions_requested": 10,
        "ai_assistant_messages": 10,
        "recipes_imported": 5,
    },
}

# Pre-launch allowances. Existing rows keep these; new accounts do not.
LEGACY_USAGE_LIMITS = {
    "pro": {
        "ai_images_generated": 150,
        "ai_suggestions_requested": 300,
        "ai_assistant_messages": 500,
        "recipes_imported": 100,
    },
    "free": {
        "ai_images_generated": 3,
        "ai_suggestions_requested": 10,
        "ai_assistant_messages": 10,
        "recipes_imported": 5,
    },
}

# Fits user_usage.month (String(7)) and does not collide with YYYY-MM.
TRIAL_USAGE_WINDOW = "trial"

# Pro caps for a household of 2+ when usage is pooled on the owner (#208).
HOUSEHOLD_PRO_CAP_MULTIPLIER = 1.5

UsageSubjectResolver = Callable[["User"], "User"]
HouseholdMultiplier = Callable[["User"], float]


def identity_usage_subject(user: User) -> User:
    """Default meter: the person who made the request."""
    return user


def no_household_multiplier(user: User) -> float:
    """Default multiplier. Household sharing replaces this. ``user`` is unused."""
    del user
    return 1.0


_usage_subject_resolver: UsageSubjectResolver = identity_usage_subject
_household_multiplier: HouseholdMultiplier = no_household_multiplier


def set_household_usage_hooks(
    *,
    subject: UsageSubjectResolver | None = None,
    multiplier: HouseholdMultiplier | None = None,
) -> None:
    """Register household sharing (#208) without editing this module again.

    ``subject`` should return the household owner when usage is pooled.
    ``multiplier`` should return ``HOUSEHOLD_PRO_CAP_MULTIPLIER`` (1.5) for
    that owner when the household has 2 or more people, and 1.0 otherwise.
    The reserve path in ``require_within_usage_limit`` calls ``usage_meter``,
    which applies both hooks. Caps for trial, free, expired, and none are not scaled.
    """
    global _usage_subject_resolver, _household_multiplier
    if subject is not None:
        _usage_subject_resolver = subject
    if multiplier is not None:
        _household_multiplier = multiplier


def usage_subject(user: User) -> User:
    """Whose usage row and cap this request counts against."""
    return _usage_subject_resolver(user)


def household_cap_multiplier(user: User) -> float:
    """Pro-cap scale for ``user``. 1.0 until household sharing registers a hook."""
    return _household_multiplier(user)


def scale_cap(limit: Optional[int], multiplier: float) -> Optional[int]:
    """Apply a household multiplier. None stays uncapped. 1.0 is a no-op."""
    if limit is None or multiplier == 1.0:
        return limit
    return math.ceil(limit * multiplier)


def get_monthly_limit(tier: str, field: str) -> Optional[int]:
    """
    Get the cap for a usage field under a subscription tier.

    Unknown tiers fall back to the free tier's caps. None means uncapped,
    which this table does not use (admins are uncapped in the caller).
    """
    table = TIER_USAGE_LIMITS.get(tier, TIER_USAGE_LIMITS["free"])
    return table.get(field)


def usage_window_for(user: User, now: datetime | None = None) -> str:
    """Calendar month, or one stable key for the whole trial."""
    if user.usage_tier == "trial":
        return TRIAL_USAGE_WINDOW
    moment = now or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m")


def get_user_monthly_limit(user: User, field: str) -> Optional[int]:
    """Resolve the cap used for enforcement and the usage meter.

    Admins are uncapped. Trial, expired, and none ignore the legacy cohort.
    Pro and free legacy accounts keep LEGACY_USAGE_LIMITS even if they later upgrade.
    """
    if user.is_admin:
        return None
    tier = user.usage_tier
    if tier in ("trial", "expired", "none"):
        return get_monthly_limit(tier, field)
    plan = getattr(user, "usage_plan", None)
    if plan is not None and plan != "launch":
        limit = LEGACY_USAGE_LIMITS.get(tier, LEGACY_USAGE_LIMITS["free"]).get(field)
    else:
        limit = get_monthly_limit(tier, field)
    if tier == "pro":
        return scale_cap(limit, household_cap_multiplier(user))
    return limit


def usage_meter(user: User, field: str) -> tuple[User, Optional[int]]:
    """Subject and cap for one reservation.

    Household sharing (#208) changes the subject to the owner and the Pro
    multiplier to 1.5. Callers that increment usage must use the returned
    user id, not the signed-in member's id.
    """
    subject = usage_subject(user)
    if subject.is_admin:
        return subject, None
    return subject, get_user_monthly_limit(subject, field)
