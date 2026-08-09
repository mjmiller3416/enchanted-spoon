"""app/core/usage_limits.py

Monthly usage caps for Gemini-backed AI features, keyed by subscription tier.

Kept separate from `UsageService` so a metered free tier (see Phase 1 of the
public release roadmap) can add/adjust tier caps here without touching the
enforcement logic in `UsageService.check_limit` or the routes that call it.
"""

from typing import Optional

# Monthly caps per UserUsage field, per subscription tier.
# A tier/field combination with no entry is uncapped.
TIER_USAGE_LIMITS: dict[str, dict[str, int]] = {
    "pro": {
        "ai_images_generated": 150,
        "ai_suggestions_requested": 300,
        "ai_assistant_messages": 500,
        "recipes_imported": 100,
    },
    "free": {
        "ai_images_generated": 0,
        "ai_suggestions_requested": 0,
        "ai_assistant_messages": 0,
        "recipes_imported": 0,
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
