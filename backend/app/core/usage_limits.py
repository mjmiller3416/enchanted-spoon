"""app/core/usage_limits.py

Monthly usage caps for Gemini-backed AI features, keyed by subscription tier.

Kept separate from `UsageService` so a metered free tier (see Phase 1 of the
public release roadmap) can add/adjust tier caps here without touching the
enforcement logic in `UsageService.reserve` or the routes gated by it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.user import User

# Monthly caps per UserUsage field, per subscription tier.
# A tier/field combination with no entry is uncapped.
#
# Launch allowances bound optional AI use at the $4.99 price.
# One photo unit is one action (up to a reference/banner pair).
# Suggestions share a bucket across generation, nutrition, meal ideas and tips.
# Core saved-recipe, Menu and shopping use is uncapped.
TIER_USAGE_LIMITS: dict[str, dict[str, int]] = {
    "pro": {
        "ai_images_generated": 10,
        "ai_suggestions_requested": 50,
        "ai_assistant_messages": 50,
        "recipes_imported": 100,
    },
    "free": {
        "ai_images_generated": 1,
        "ai_suggestions_requested": 10,
        "ai_assistant_messages": 10,
        "recipes_imported": 5,
    },
}


def get_monthly_limit(tier: str, field: str) -> Optional[int]:
    """
    Get the monthly cap for a usage field under a subscription tier.

    Args:
        tier: Subscription tier (e.g. "pro", "free").
        field: UserUsage field name (e.g. "ai_images_generated").

    Returns:
        The monthly cap, or None if uncapped for that tier/field. Unknown
        tiers fall back to the "free" tier's caps as the safest default.
    """
    return TIER_USAGE_LIMITS.get(tier, TIER_USAGE_LIMITS["free"]).get(field)


LEGACY_USAGE_LIMITS = {
    "pro": {"ai_images_generated": 150, "ai_suggestions_requested": 300,
            "ai_assistant_messages": 500, "recipes_imported": 100},
    "free": {"ai_images_generated": 3, "ai_suggestions_requested": 10,
             "ai_assistant_messages": 10, "recipes_imported": 5},
}


def get_user_monthly_limit(user: User, field: str) -> Optional[int]:
    """Resolve the persisted cohort consistently for enforcement and display.

    Existing accounts keep legacy limits even if they upgrade later. Unknown
    persisted plans conservatively retain legacy entitlements. None is only for
    transient, not-yet-inserted ORM instances and uses the new-account default.
    """
    if user.is_admin:
        return None
    tier = "pro" if user.has_pro_access else "free"
    plan = getattr(user, "usage_plan", None)
    if plan is not None and plan != "launch":
        return LEGACY_USAGE_LIMITS[tier].get(field)
    return get_monthly_limit(tier, field)
