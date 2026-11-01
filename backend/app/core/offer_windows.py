"""Config dates for the founding offer and the free-plan sunset.

Both default to Mar 31, 2027, 11:59 PM America/New_York. Override with
FREE_TIER_SUNSET_AT or FOUNDER_OFFER_ENDS_AT (ISO 8601). A naive value is
read as Eastern Time. These are code defaults, not Railway variables this
change sets.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

LEGACY_CUTOFF_UNSET_ERROR = (
    "LEGACY_FREE_CUTOFF is unset. Production refuses to start until it is an "
    "ISO 8601 release timestamp. Dev and test keep every account on the "
    "legacy free plan until it is set."
)
LEGACY_CUTOFF_INVALID_ERROR = (
    "LEGACY_FREE_CUTOFF is not valid ISO 8601. Production refuses to start. "
    "Dev and test keep every account on the legacy free plan."
)

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


def legacy_free_cutoff() -> datetime | None:
    """Accounts created before this instant keep free until the sunset date.

    This is the coordinated release deploy time, not a date baked into the
    source. Set ``LEGACY_FREE_CUTOFF`` (ISO 8601) before a production deploy.
    A naive value is read as Eastern Time. Production refuses to start when
    it is missing or unparseable. Dev and test treat that as every account
    being legacy. PR #209 should read the same variable instead of its
    hardcoded 2026-10-31 cutoff.
    """
    parsed, _problem = _parse_legacy_cutoff()
    return parsed


def legacy_cutoff_issue() -> str | None:
    """Why production must not start, or None when the cutoff parses."""
    _parsed, problem = _parse_legacy_cutoff()
    return problem


def _parse_legacy_cutoff() -> tuple[datetime | None, str | None]:
    raw = os.getenv("LEGACY_FREE_CUTOFF", "").strip()
    if not raw:
        return None, LEGACY_CUTOFF_UNSET_ERROR
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        logger.error(LEGACY_CUTOFF_INVALID_ERROR)
        return None, LEGACY_CUTOFF_INVALID_ERROR
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=EASTERN)
    return parsed, None


def created_before_legacy_free_cutoff(created_at: datetime | None) -> bool:
    """True when ``created_at`` is strictly before ``LEGACY_FREE_CUTOFF``.

    Dev and test treat a missing or unparseable cutoff as legacy. Production
    does not: startup refuses to run, and a request that still sees no
    cutoff does not grandfather anyone.
    """
    cutoff = legacy_free_cutoff()
    if cutoff is None:
        from .startup import is_production

        return not is_production()
    if created_at is None:
        return False
    moment = created_at if created_at.tzinfo else created_at.replace(tzinfo=EASTERN)
    return moment.astimezone(EASTERN) < cutoff.astimezone(EASTERN)


def legacy_cutoff_status() -> dict[str, object]:
    """Health and admin status payload for the free-tier cutoff."""
    issue = legacy_cutoff_issue()
    cutoff = legacy_free_cutoff()
    if issue is not None or cutoff is None:
        return {
            "legacy_free_cutoff_configured": False,
            "legacy_free_cutoff": None,
            "legacy_free_cutoff_error": issue or LEGACY_CUTOFF_UNSET_ERROR,
        }
    return {
        "legacy_free_cutoff_configured": True,
        "legacy_free_cutoff": cutoff.isoformat(),
        "legacy_free_cutoff_error": None,
    }


def log_legacy_cutoff_if_unset() -> None:
    """Dev/test warning. Production fails in ``validate_config`` instead."""
    issue = legacy_cutoff_issue()
    if issue is None:
        return
    from .startup import is_production

    if is_production():
        logger.critical(issue)
        return
    logger.warning(issue)


def sunset_is_due(now: datetime | None = None) -> bool:
    moment = now or datetime.now(EASTERN)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=EASTERN)
    return moment > free_tier_sunset_at()
