"""Register device tokens and send trial nudges through APNs or FCM.

Credentials are optional. Registration and scheduling work without them.
Dispatch leaves nudges unsent until APNs and FCM are configured, so a cron
can retry after the keys exist.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from jose import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.device_token import DeviceToken
from ..models.trial_nudge import TrialNudge
from ..models.user import User

logger = logging.getLogger(__name__)

NUDGE_COPY = {
    "trial_day_5": (
        "2 days left on your Pro trial",
        "Your Enchanted Spoon Pro trial ends in two days. Cancel anytime before then.",
    ),
    "trial_day_6": (
        "Your Pro trial ends tomorrow",
        "You'll be billed when the trial ends unless you cancel in the store.",
    ),
}


def nudge_schedule(trial_started_at: datetime) -> list[tuple[str, datetime]]:
    """Remote trial nudges: day 5 and day 6 after the trial starts."""
    start = trial_started_at if trial_started_at.tzinfo else trial_started_at.replace(tzinfo=timezone.utc)
    return [
        ("trial_day_5", start + timedelta(days=5)),
        ("trial_day_6", start + timedelta(days=6)),
    ]


class PushNotConfiguredError(Exception):
    """Raised when a platform's push credentials are missing."""


class PushService:
    """Device tokens and trial nudge delivery."""

    def __init__(self, session: Session):
        self.session = session

    def register_token(self, user: User, token: str, platform: str) -> DeviceToken:
        """Store a token for this account. The same token is moved if it changes owner."""
        platform = platform.strip().lower()
        if platform not in {"ios", "android"}:
            raise ValueError("platform must be ios or android")
        token = token.strip()
        if not token:
            raise ValueError("token is required")

        existing = self.session.scalars(select(DeviceToken).where(DeviceToken.token == token)).first()
        if existing is None:
            existing = DeviceToken(user_id=user.id, token=token, platform=platform)
            self.session.add(existing)
        else:
            existing.user_id = user.id
            existing.platform = platform
            existing.updated_at = datetime.now(timezone.utc)
        self.session.flush()
        return existing

    def unregister_token(self, user: User, token: str) -> None:
        row = self.session.scalars(
            select(DeviceToken).where(DeviceToken.token == token, DeviceToken.user_id == user.id)
        ).first()
        if row is not None:
            self.session.delete(row)
            self.session.flush()

    def schedule_trial_nudges(self, user: User, trial_started_at: Optional[datetime] = None) -> int:
        """Insert day-5 and day-6 nudges once. Returns how many rows were added."""
        started = trial_started_at or user.trial_consumed_at or datetime.now(timezone.utc)
        added = 0
        for kind, send_at in nudge_schedule(started):
            existing = self.session.scalars(
                select(TrialNudge).where(TrialNudge.user_id == user.id, TrialNudge.kind == kind)
            ).first()
            if existing is not None:
                continue
            self.session.add(TrialNudge(user_id=user.id, kind=kind, send_at=send_at))
            added += 1
        self.session.flush()
        return added

    def dispatch_due(self, now: Optional[datetime] = None) -> dict[str, int | str]:
        """Send nudges whose time has come. Unconfigured platforms stay queued."""
        now = now or datetime.now(timezone.utc)
        due = list(
            self.session.scalars(
                select(TrialNudge).where(TrialNudge.sent_at.is_(None), TrialNudge.send_at <= now)
            )
        )
        sent = 0
        skipped = 0
        for nudge in due:
            title, body = NUDGE_COPY[nudge.kind]
            tokens = list(
                self.session.scalars(select(DeviceToken).where(DeviceToken.user_id == nudge.user_id))
            )
            if not tokens:
                skipped += 1
                continue
            delivered = False
            for device in tokens:
                try:
                    send_push(device.platform, device.token, title, body)
                    delivered = True
                except PushNotConfiguredError:
                    logger.info("Push for %s is not configured; leaving %s queued", device.platform, nudge.kind)
                except Exception:
                    logger.exception("Push delivery failed for user %s", nudge.user_id)
            if delivered:
                nudge.sent_at = now
                sent += 1
            else:
                skipped += 1
        self.session.flush()
        self.session.commit()
        return {"sent": sent, "skipped": skipped}


def send_push(platform: str, token: str, title: str, body: str) -> None:
    """Deliver one notification. Raises PushNotConfiguredError when keys are absent."""
    import os

    if platform == "ios":
        key_id = os.environ.get("APNS_KEY_ID")
        team_id = os.environ.get("APNS_TEAM_ID")
        auth_key = os.environ.get("APNS_AUTH_KEY")
        if not (key_id and team_id and auth_key):
            raise PushNotConfiguredError("Set APNS_KEY_ID, APNS_TEAM_ID, and APNS_AUTH_KEY.")
        _send_apns(token, title, body, key_id, team_id, auth_key.replace("\\n", "\n"))
        return
    server_key = os.environ.get("FCM_SERVER_KEY")
    if not server_key:
        raise PushNotConfiguredError("Set FCM_SERVER_KEY.")
    _send_fcm(token, title, body, server_key)


def _send_apns(token: str, title: str, body: str, key_id: str, team_id: str, auth_key: str) -> None:
    import os

    bundle = os.environ.get("APNS_BUNDLE_ID", "com.enchantedspoon.app")
    sandbox = os.environ.get("APNS_USE_SANDBOX", "true").lower() != "false"
    host = "https://api.sandbox.push.apple.com" if sandbox else "https://api.push.apple.com"
    claims = {"iss": team_id, "iat": int(time.time())}
    signed = jwt.encode(claims, auth_key, algorithm="ES256", headers={"kid": key_id})
    response = httpx.post(
        f"{host}/3/device/{token}",
        headers={
            "authorization": f"bearer {signed}",
            "apns-topic": bundle,
            "apns-push-type": "alert",
        },
        json={"aps": {"alert": {"title": title, "body": body}, "sound": "default"}},
        timeout=15.0,
    )
    if response.status_code >= 400:
        logger.warning("APNs rejected a trial nudge: %s %s", response.status_code, response.text)


def _send_fcm(token: str, title: str, body: str, server_key: str) -> None:
    response = httpx.post(
        "https://fcm.googleapis.com/fcm/send",
        headers={"Authorization": f"key={server_key}", "Content-Type": "application/json"},
        content=json.dumps({"to": token, "notification": {"title": title, "body": body}}),
        timeout=15.0,
    )
    if response.status_code >= 400:
        logger.warning("FCM rejected a trial nudge: %s %s", response.status_code, response.text)
