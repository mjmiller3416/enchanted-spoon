"""app/core/usage_limits.py

Usage caps for Gemini-backed AI features.

Launch accounts use the approved cost-control caps. Accounts persisted as
`usage_plan=legacy` (see the soft-launch migration) keep their previous
allowances. Trial caps cover the whole trial, not a calendar month. Expired
and read-only accounts are capped at zero. Unknown tiers fall back to free.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

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

    Admins are uncapped. Trial and expired ignore the legacy cohort. Pro and
    free legacy accounts keep LEGACY_USAGE_LIMITS even if they later upgrade.
    """
    if user.is_admin:
        return None
    tier = user.usage_tier
    if tier in ("trial", "expired"):
        return get_monthly_limit(tier, field)
    plan = getattr(user, "usage_plan", None)
    if plan is not None and plan != "launch":
        return LEGACY_USAGE_LIMITS.get(tier, LEGACY_USAGE_LIMITS["free"]).get(field)
    return get_monthly_limit(tier, field)
