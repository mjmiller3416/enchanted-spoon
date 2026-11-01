"""Move legacy free accounts to read-only and queue sunset reminders.

The date check is the schedule. Before Mar 31, 2027, 11:59 PM ET this is a
no-op for the migration. Reminders are due 30, 7, and 1 days before that
moment. Push and email are hooks: they are logged, and posted to
SUNSET_REMINDER_WEBHOOK_URL when that env var is set. Nothing is sent from
this process to a mailbox directly.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.offer_windows import free_tier_sunset_at, sunset_is_due
from ..models.user import User

logger = logging.getLogger(__name__)

REMINDER_COPY = {
    "30": "30 days left on the free plan. Lock in a founding price before Mar 31: FOUNDER30 (monthly) or FOUNDER30Y (annual).",
    "7": "1 week left: free accounts go read-only on Mar 31. Your recipes stay safe. FOUNDER30 and FOUNDER30Y end the same night.",
    "1": "Last day tomorrow: the free plan, FOUNDER30 and FOUNDER30Y all end Mar 31 at 11:59 PM ET.",
}


def apply_free_tier_sunset(session: Session, now: datetime | None = None) -> int:
    """Mark legacy free accounts read-only once the sunset date has passed."""
    moment = now or datetime.now(timezone.utc)
    if not sunset_is_due(moment):
        return 0
    from ..core.offer_windows import legacy_free_cutoff

    if legacy_free_cutoff() is None:
        return 0
    changed = 0
    rows = session.scalars(
        select(User).where(
            User.subscription_tier == "free",
            User.subscription_status == "active",
            User.has_used_trial.is_(False),
            User.is_admin.is_(False),
            User.read_only_at.is_(None),
        )
    ).all()
    for user in rows:
        if not user.is_legacy_free_account() or user.has_pro_access:
            continue
        user.read_only_at = moment
        changed += 1
    return changed


def _sent_map(user: User) -> dict[str, datetime | None]:
    return {
        "30": user.sunset_reminder_30_sent_at,
        "7": user.sunset_reminder_7_sent_at,
        "1": user.sunset_reminder_1_sent_at,
    }


def due_reminder_kind(user: User, now: datetime | None = None) -> str | None:
    """The closest unsent reminder that is already due, if the user still qualifies."""
    if not user.is_legacy_free_account() or user.is_read_only:
        return None
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    remaining = free_tier_sunset_at() - moment.astimezone(free_tier_sunset_at().tzinfo)
    if remaining.total_seconds() <= 0:
        return None
    sent = _sent_map(user)
    for days, kind in ((1, "1"), (7, "7"), (30, "30")):
        if remaining <= timedelta(days=days) and sent[kind] is None:
            return kind
    return None


def _mark_sent(user: User, kind: str, now: datetime) -> None:
    # Sending the closest reminder also closes coarser ones so a late job
    # does not deliver three messages at once.
    if kind == "1":
        user.sunset_reminder_30_sent_at = user.sunset_reminder_30_sent_at or now
        user.sunset_reminder_7_sent_at = user.sunset_reminder_7_sent_at or now
        user.sunset_reminder_1_sent_at = now
    elif kind == "7":
        user.sunset_reminder_30_sent_at = user.sunset_reminder_30_sent_at or now
        user.sunset_reminder_7_sent_at = now
    else:
        user.sunset_reminder_30_sent_at = now


def dispatch_reminder(user: User, kind: str) -> None:
    """Push and email hooks. Delivery itself is outside this process."""
    copy = REMINDER_COPY[kind]
    logger.info("sunset_reminder channel=email kind=%s user_id=%s", kind, user.id)
    logger.info("sunset_reminder channel=push kind=%s user_id=%s", kind, user.id)
    url = os.getenv("SUNSET_REMINDER_WEBHOOK_URL", "").strip()
    if not url:
        return
    httpx.post(
        url,
        json={"user_id": user.id, "email": user.email, "kind": kind, "copy": copy, "channels": ["email", "push"]},
        timeout=10.0,
    )


def send_due_reminders(session: Session, now: datetime | None = None) -> int:
    moment = now or datetime.now(timezone.utc)
    if sunset_is_due(moment):
        return 0
    sent = 0
    rows = session.scalars(
        select(User).where(
            User.subscription_tier == "free",
            User.subscription_status == "active",
            User.has_used_trial.is_(False),
            User.is_admin.is_(False),
        )
    ).all()
    for user in rows:
        kind = due_reminder_kind(user, moment)
        if kind is None:
            continue
        dispatch_reminder(user, kind)
        _mark_sent(user, kind, moment)
        sent += 1
    return sent
