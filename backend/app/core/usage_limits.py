"""app/core/usage_limits.py

Usage caps for Gemini-backed AI features.

Pro subscribers and granted testers use the launch Pro caps, including
accounts persisted as ``usage_plan=legacy``. A usage-exempt account (the
``usage_exempt`` flag, an id in ``USAGE_EXEMPT_USER_IDS``, or a Clerk-verified
primary email in ``ADMIN_EXEMPT_EMAILS``) keeps the pre-release Pro
allowances. A verified primary on ``ADMIN_EXEMPT_EMAILS`` is uncapped for
AI only. Admin views and mutations require ``is_admin`` or
``USAGE_EXEMPT_USER_IDS``.
Legacy free accounts still use the free caps.
Trial caps cover the whole trial, not a calendar month. Expired and
read-only accounts are capped at zero. Accounts created on or after
``LEGACY_FREE_CUTOFF`` use the ``none`` tier (also zero). Unknown tiers fall
back to free.
"""

from __future__ import annotations

import math
import os
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

# Pre-release Pro allowances. Applied only when an account is usage-exempt.
# The free row is still the legacy free plan until the sunset date.
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
    which applies both hooks. The multiplier scales the resolved Pro cap,
    including the pre-release allowances on a usage-exempt account. Caps for
    trial, free, expired, and none are not scaled.
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


def usage_exempt_user_ids() -> set[int]:
    """User ids in ``USAGE_EXEMPT_USER_IDS`` (comma-separated). Invalid tokens are ignored."""
    raw = os.getenv("USAGE_EXEMPT_USER_IDS", "")
    ids: set[int] = set()
    for part in raw.split(","):
        token = part.strip()
        if token.isdigit():
            ids.add(int(token))
    return ids


def admin_exempt_emails() -> set[str]:
    """Emails in ``ADMIN_EXEMPT_EMAILS``. Commas split, spaces are trimmed, case is ignored."""
    raw = os.getenv("ADMIN_EXEMPT_EMAILS", "")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def remember_verified_primary_email(user: User, email: Optional[str]) -> None:
    """Stash the Clerk-verified primary email on this request's user object.

    The database ``email`` column is not consulted. An unverified claim,
    a secondary address, or a missing Clerk lookup stores None.
    """
    normalized = email.strip().lower() if isinstance(email, str) and email.strip() else None
    setattr(user, "clerk_verified_primary_email", normalized)


def is_admin_exempt_email(user: User) -> bool:
    """True when this request's Clerk-verified primary email is allowlisted.

    The stored ``user.email`` is ignored. Only ``remember_verified_primary_email``
    can set a match, and that value comes from Clerk's primary address when
    its verification status is ``verified``.
    """
    email = getattr(user, "clerk_verified_primary_email", None)
    if not isinstance(email, str) or not email:
        return False
    return email in admin_exempt_emails()


def _usage_exempt_user_id(user: User) -> bool:
    user_id = getattr(user, "id", None)
    if type(user_id) is not int:
        return False
    return user_id in usage_exempt_user_ids()


def can_view_admin(user: User) -> bool:
    """Admin reads: the database flag or ``USAGE_EXEMPT_USER_IDS`` only.

    ``ADMIN_EXEMPT_EMAILS`` lifts usage caps and does not open admin views.
    """
    if user.is_admin:
        return True
    return _usage_exempt_user_id(user)


def can_mutate_admin(user: User) -> bool:
    """Admin writes require the database flag or ``USAGE_EXEMPT_USER_IDS``.

    ``ADMIN_EXEMPT_EMAILS`` is intentionally not accepted here.
    """
    if getattr(user, "is_admin", False) is True:
        return True
    return _usage_exempt_user_id(user)


def is_usage_exempt(user: User) -> bool:
    """True for the admin override: flag, id allowlist, or exempt email.

    A MagicMock flag is not an exemption. Only a real ``True``, an integer
    id in ``USAGE_EXEMPT_USER_IDS``, or a verified primary email in
    ``ADMIN_EXEMPT_EMAILS`` counts. The email match uncaps AI and does not
    grant admin access.
    """
    if getattr(user, "usage_exempt", False) is True:
        return True
    if is_admin_exempt_email(user):
        return True
    return _usage_exempt_user_id(user)


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

    Admins, including emails in ``ADMIN_EXEMPT_EMAILS``, are uncapped. Trial,
    expired, and none ignore exemptions and the legacy cohort. Pro subscribers
    and granted testers use the launch Pro caps. Usage-exempt Pro accounts
    keep LEGACY_USAGE_LIMITS["pro"]. Legacy free accounts still use the free row.
    """
    if user.is_admin or is_admin_exempt_email(user):
        return None
    tier = user.usage_tier
    if tier in ("trial", "expired", "none"):
        return get_monthly_limit(tier, field)
    if tier == "pro":
        if is_usage_exempt(user):
            limit = LEGACY_USAGE_LIMITS["pro"].get(field)
        else:
            limit = get_monthly_limit("pro", field)
        return scale_cap(limit, household_cap_multiplier(user))
    plan = getattr(user, "usage_plan", None)
    if plan is not None and plan != "launch":
        return LEGACY_USAGE_LIMITS.get(tier, LEGACY_USAGE_LIMITS["free"]).get(field)
    return get_monthly_limit(tier, field)


def usage_meter(user: User, field: str) -> tuple[User, Optional[int]]:
    """Subject and cap for one reservation.

    Household sharing (#208) changes the subject to the owner and the Pro
    multiplier to 1.5. Callers that increment usage must use the returned
    user id, not the signed-in member's id.
    """
    subject = usage_subject(user)
    if subject.is_admin or is_admin_exempt_email(subject):
        return subject, None
    return subject, get_user_monthly_limit(subject, field)
