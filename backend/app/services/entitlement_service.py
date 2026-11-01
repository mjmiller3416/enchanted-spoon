"""Unify App Store and Play Billing entitlements with one account.

RevenueCat is the store client (StoreKit 2 and Play Billing). This service
is the server of record: it applies webhook events and subscriber snapshots
onto the user, and it refuses a second free trial when the account already
consumed one on Stripe or on the other store.

Stripe subscriptions stay on the Stripe columns. Store subscriptions stay
on the store columns. ``User.has_pro_access`` is true when either is current,
so a person is never double-charged into a second trial and a paid store
receipt is never dropped because they also have a Stripe customer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import httpx
from sqlalchemy.orm import Session

from ..core.native_billing_config import (
    PRO_ENTITLEMENT_ID,
    NativeBillingSettings,
    get_native_billing_settings,
)
from ..models.user import User
from ..repositories.user_repo import UserRepo

logger = logging.getLogger(__name__)

# RevenueCat store names, webhook (upper) and REST (lower).
STORE_PROVIDERS = {
    "APP_STORE": "app_store",
    "MAC_APP_STORE": "app_store",
    "PLAY_STORE": "play_store",
    "app_store": "app_store",
    "mac_app_store": "app_store",
    "play_store": "play_store",
}

# Events that change entitlement. Stripe events forwarded by RevenueCat are
# ignored; the Stripe webhook owns that column set.
GRANTING_EVENT_TYPES = {
    "INITIAL_PURCHASE",
    "RENEWAL",
    "UNCANCELLATION",
    "PRODUCT_CHANGE",
    "SUBSCRIPTION_EXTENDED",
    "NON_RENEWING_PURCHASE",
    "TEMPORARY_ENTITLEMENT_GRANT",
}
HANDLED_EVENT_TYPES = GRANTING_EVENT_TYPES | {"CANCELLATION", "EXPIRATION", "BILLING_ISSUE"}

REVENUECAT_SUBSCRIBER_URL = "https://api.revenuecat.com/v1/subscribers/{app_user_id}"


class NativeIapDisabledError(Exception):
    """Raised when a store call is made while native IAP is switched off."""


class NativeIapNotConfiguredError(Exception):
    """Raised when RevenueCat credentials required for the call are missing."""


class RevenueCatApiError(Exception):
    """Raised when the RevenueCat REST API rejects or fails a subscriber read."""


class UnknownStoreUserError(Exception):
    """Raised when a webhook names an app user id we cannot resolve.

    The route turns this into a 5xx so RevenueCat retries. A purchase can
    arrive before the account row exists.
    """


@dataclass
class EventDecision:
    """What to write for one store event. ``trial`` is claimed before apply."""

    result: str
    updates: dict[str, Any] = field(default_factory=dict)
    trial: Optional[tuple[str, Optional[str]]] = None


def _ms_to_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _provider(store: Any) -> Optional[str]:
    if not isinstance(store, str):
        return None
    return STORE_PROVIDERS.get(store) or STORE_PROVIDERS.get(store.upper())


def decide_revenuecat_event(user: User, event: Mapping[str, Any]) -> EventDecision:
    """Map one RevenueCat webhook event onto store columns.

    Does not touch the database. A trial the account may not start comes
    back as ``trial`` so the caller can suppress it.
    """
    provider = _provider(event.get("store"))
    event_type = str(event.get("type") or "")
    if provider is None or event_type not in HANDLED_EVENT_TYPES:
        return EventDecision(result="ignored")

    timestamp = event.get("event_timestamp_ms")
    timestamp_ms = int(timestamp) if isinstance(timestamp, (int, float)) else None
    if (
        timestamp_ms is not None
        and user.store_event_timestamp_ms is not None
        and timestamp_ms < user.store_event_timestamp_ms
    ):
        return EventDecision(result="stale")

    expiration = _ms_to_datetime(event.get("expiration_at_ms"))
    transaction_id = event.get("original_transaction_id") or event.get("transaction_id")
    updates: dict[str, Any] = {
        "store_provider": provider,
        "store_expires_at": expiration,
        "store_environment": (str(event.get("environment")).lower() if event.get("environment") else None),
    }
    if event.get("product_id"):
        updates["store_product_id"] = str(event["product_id"])
    if transaction_id:
        updates["store_original_transaction_id"] = str(transaction_id)
    if timestamp_ms is not None:
        updates["store_event_timestamp_ms"] = timestamp_ms

    now = datetime.now(timezone.utc)
    expired = expiration is not None and expiration <= now

    if event_type == "EXPIRATION" or expired and event_type == "CANCELLATION":
        updates["store_status"] = "expired"
        updates["store_will_renew"] = False
        return EventDecision(result="applied", updates=updates)

    if event_type == "CANCELLATION":
        status = user.store_status if user.store_status in {"active", "trialing", "past_due"} else "active"
        updates["store_status"] = "expired" if expired else status
        updates["store_will_renew"] = False
        return EventDecision(result="applied", updates=updates)

    if event_type == "BILLING_ISSUE":
        updates["store_status"] = "expired" if expired else "past_due"
        updates["store_will_renew"] = not expired
        return EventDecision(result="applied", updates=updates)

    period = str(event.get("period_type") or "").upper()
    if period == "TRIAL" and not expired:
        updates["store_status"] = "trialing"
        updates["store_will_renew"] = True
        tx = str(transaction_id) if transaction_id else None
        return EventDecision(result="applied", updates=updates, trial=(provider, tx))

    updates["store_status"] = "expired" if expired else "active"
    updates["store_will_renew"] = not expired
    return EventDecision(result="applied", updates=updates)


def decide_subscriber_snapshot(
    user: User,
    payload: Mapping[str, Any],
    *,
    entitlement_id: str = PRO_ENTITLEMENT_ID,
    now: Optional[datetime] = None,
) -> EventDecision:
    """Map a RevenueCat ``GET /subscribers`` body onto store columns."""
    now = now or datetime.now(timezone.utc)
    subscriber = payload.get("subscriber") if isinstance(payload.get("subscriber"), Mapping) else {}
    entitlements = subscriber.get("entitlements") if isinstance(subscriber, Mapping) else None
    entitlements = entitlements if isinstance(entitlements, Mapping) else {}
    pro = entitlements.get(entitlement_id)
    if not isinstance(pro, Mapping):
        if user.store_status:
            return EventDecision(
                result="applied",
                updates={
                    "store_status": "expired",
                    "store_will_renew": False,
                    "store_event_timestamp_ms": int(now.timestamp() * 1000),
                },
            )
        return EventDecision(result="ignored")

    product_id = pro.get("product_identifier")
    subscriptions = subscriber.get("subscriptions") if isinstance(subscriber, Mapping) else None
    subscriptions = subscriptions if isinstance(subscriptions, Mapping) else {}
    sub = subscriptions.get(product_id) if product_id else None
    sub = sub if isinstance(sub, Mapping) else {}
    provider = _provider(sub.get("store"))
    if provider is None:
        # Stripe (and other non-store) entitlements are owned by the Stripe webhook.
        return EventDecision(result="ignored")

    expiration = _parse_iso(pro.get("expires_date"))
    expired = expiration is not None and expiration <= now
    period = str(pro.get("period_type") or sub.get("period_type") or "").upper()
    if expired:
        status = "expired"
    elif sub.get("billing_issues_detected_at"):
        status = "past_due"
    elif period == "TRIAL":
        status = "trialing"
    else:
        status = "active"

    updates: dict[str, Any] = {
        "store_provider": provider,
        "store_status": status,
        "store_expires_at": expiration,
        "store_will_renew": status != "expired" and not sub.get("unsubscribe_detected_at"),
        "store_environment": "sandbox" if sub.get("is_sandbox") else "production",
        "store_event_timestamp_ms": int(now.timestamp() * 1000),
    }
    if product_id:
        updates["store_product_id"] = str(product_id)

    trial = (provider, None) if status == "trialing" else None
    return EventDecision(result="applied", updates=updates, trial=trial)


class EntitlementService:
    """Apply store entitlement decisions and commit them."""

    def __init__(self, session: Session, settings: NativeBillingSettings | None = None):
        self.session = session
        self.repo = UserRepo(session)
        self.settings = settings or get_native_billing_settings()

    def require_enabled(self) -> None:
        if not self.settings.native_iap_enabled:
            raise NativeIapDisabledError(
                "In-app purchases are turned off. Set NATIVE_IAP_ENABLED=true to enable them."
            )

    def apply_revenuecat_event(self, event: Mapping[str, Any]) -> str:
        """Apply one webhook event. Commits when the event changes a user.

        Raises:
            UnknownStoreUserError: ``app_user_id`` is numeric but no user has that id.
        """
        app_user_id = str(event.get("app_user_id") or "")
        if not app_user_id or app_user_id.startswith("$RCAnonymousID"):
            logger.info("Ignoring RevenueCat event with anonymous app_user_id")
            return "ignored"

        try:
            user_id = int(app_user_id)
        except ValueError:
            logger.warning("RevenueCat app_user_id is not an account id: %s", app_user_id)
            return "ignored"

        user = self.repo.get_by_id(user_id)
        if user is None:
            raise UnknownStoreUserError(f"No user with id {user_id}")

        decision = decide_revenuecat_event(user, event)
        if decision.result in {"ignored", "stale"}:
            return decision.result

        self._apply(user, decision)
        self.session.commit()
        return decision.result

    def sync_from_revenuecat(self, user: User) -> str:
        """Read the subscriber from RevenueCat and apply it. Requires the flag and API key."""
        self.require_enabled()
        if not self.settings.api_configured or not self.settings.revenuecat_secret_api_key:
            raise NativeIapNotConfiguredError(
                "RevenueCat is not configured. Set REVENUECAT_SECRET_API_KEY."
            )

        payload = self._fetch_subscriber(str(user.id), self.settings.revenuecat_secret_api_key)
        decision = decide_subscriber_snapshot(
            user,
            payload,
            entitlement_id=self.settings.revenuecat_entitlement_id,
        )
        if decision.result == "ignored":
            return decision.result
        self._apply(user, decision)
        self.session.commit()
        return decision.result

    def _apply(self, user: User, decision: EventDecision) -> None:
        if decision.trial is not None:
            provider, transaction_id = decision.trial
            if not self.repo.claim_trial(user, provider, transaction_id):
                decision.updates["store_status"] = "trial_suppressed"
                decision.updates["store_will_renew"] = False
                decision.result = "trial_suppressed"
                logger.info(
                    "Suppressed a second free trial for user %s from %s",
                    user.id,
                    provider,
                )
        self.repo.apply_store_fields(user, decision.updates)
        if decision.result == "applied" and decision.updates.get("store_status") == "trialing":
            from .push_service import PushService

            PushService(self.session).schedule_trial_nudges(user)

    def _fetch_subscriber(self, app_user_id: str, api_key: str) -> dict[str, Any]:
        url = REVENUECAT_SUBSCRIBER_URL.format(app_user_id=app_user_id)
        try:
            response = httpx.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15.0,
            )
        except httpx.HTTPError as exc:
            logger.error("RevenueCat subscriber fetch failed for %s: %s", app_user_id, exc)
            raise RevenueCatApiError("Couldn't reach the store billing service.") from exc

        if response.status_code == 404:
            return {}
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "RevenueCat subscriber fetch returned %s for %s",
                response.status_code,
                app_user_id,
            )
            raise RevenueCatApiError("The store billing service rejected the entitlement check.") from exc
        body = response.json()
        return body if isinstance(body, dict) else {}
