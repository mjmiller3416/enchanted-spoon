"""Config dates for the founding offer and the free-plan sunset.

Both default to Mar 31, 2027, 11:59 PM America/New_York. Override with
FREE_TIER_SUNSET_AT or FOUNDER_OFFER_ENDS_AT (ISO 8601). A naive value is
read as Eastern Time. These are code defaults, not Railway variables this
change sets.
"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")

# 11:59 PM ET. March 31, 2027 is EDT (UTC-4), so this is 2027-04-01T03:59:00Z.
_DEFAULT_DEADLINE = datetime(2027, 3, 31, 23, 59, tzinfo=EASTERN)


def _parse_deadline(env_name: str) -> datetime:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return _DEFAULT_DEADLINE
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=EASTERN)
    return parsed.astimezone(EASTERN)


def free_tier_sunset_at() -> datetime:
    """When remaining legacy free accounts become read-only."""
    return _parse_deadline("FREE_TIER_SUNSET_AT")


def founder_offer_ends_at() -> datetime:
    """When FOUNDER30 and FOUNDER30Y stop being accepted at checkout."""
    return _parse_deadline("FOUNDER_OFFER_ENDS_AT")


def sunset_is_due(now: datetime | None = None) -> bool:
    moment = now or datetime.now(EASTERN)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=EASTERN)
    return moment > free_tier_sunset_at()
