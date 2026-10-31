"""Signature-verified billing wake-ups, reconciled from current Stripe state.

Snapshots are not applied to entitlements: delivery order is not authoritative.
The receipt and user update commit together. Sensitive payloads are never persisted.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import stripe
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.stripe_config import STRIPE_API_VERSION, StripeSettings, get_stripe_settings
from ..models.billing_event import BillingEvent
from ..models.user import User

logger = logging.getLogger(__name__)


class InvalidStripeSignatureError(Exception):
    """Untrusted signature, mode, or unsupported snapshot version."""


class StripeWebhookProcessingError(Exception):
    """Retryable failure; no receipt or entitlement change was committed."""


REVIEW_EVENT_TYPES = {
    "charge.refunded", "charge.dispute.created", "radar.early_fraud_warning.created",
}
RECONCILE_EVENT_TYPES = {
    "checkout.session.completed", "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed", "invoice.paid", "invoice.payment_failed",
    "customer.subscription.created", "customer.subscription.updated",
    "customer.subscription.deleted",
}
HANDLED_EVENT_TYPES = REVIEW_EVENT_TYPES | RECONCILE_EVENT_TYPES


def _plain(value: Any) -> dict:
    return value.to_dict() if hasattr(value, "to_dict") else value


class StripeWebhookService:
    def __init__(self, session: Session, settings: StripeSettings | None = None):
        self.session = session
        self.settings = settings or get_stripe_settings()

    def verify_and_parse_event(self, payload: bytes, signature: str | None,
                               settings: StripeSettings) -> stripe.Event:
        if not settings.stripe_webhook_secret or not signature:
            raise InvalidStripeSignatureError("Webhook signing configuration or signature missing")
        try:
            event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            failure = InvalidStripeSignatureError("Invalid webhook signature or payload")
        else:
            data = _plain(event)
            from app.core.startup import is_production
            key = settings.stripe_secret_key or ""
            expected_mode = True if key.startswith(("sk_live_", "rk_live_")) else False if key.startswith(("sk_test_", "rk_test_")) else None
            if is_production() and data.get("livemode") is not True:
                raise InvalidStripeSignatureError("Test-mode events are not accepted in production")
            if expected_mode is not None and data.get("livemode") is not expected_mode:
                raise InvalidStripeSignatureError("Webhook mode does not match billing configuration")
            if data.get("api_version") != STRIPE_API_VERSION:
                raise InvalidStripeSignatureError("Unsupported webhook snapshot version")
            return event
        raise failure from None

    def handle_event(self, event: stripe.Event | dict) -> None:
        event = _plain(event)
        kind = event.get("type")
        if kind not in HANDLED_EVENT_TYPES:
            return
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id or len(event_id) > 255:
            raise StripeWebhookProcessingError("Missing or invalid event identifier")
        try:
            if self.session.get(BillingEvent, event_id) is not None:
                return
            if kind in REVIEW_EVENT_TYPES:
                outcome = "review_required"
            else:
                data = _plain(event.get("data", {}).get("object", {}))
                if kind.startswith("checkout.") and data.get("mode") != "subscription":
                    outcome = "ignored_checkout_mode"
                else:
                    # The app creates/persists this mapping before checkout. Never
                    # attach an event using its externally supplied client_reference_id.
                    customer = data.get("customer")
                    user = self.session.scalar(select(User).where(
                        User.stripe_customer_id == customer
                    ).with_for_update()) if isinstance(customer, str) and customer else None
                    if user is None:
                        outcome = "review_unknown_customer"
                    else:
                        # PostgreSQL row lock serializes refresh + write for one user.
                        # Recheck after acquiring it, in case another request committed.
                        if self.session.get(BillingEvent, event_id) is not None:
                            return
                        outcome = self._reconcile(user, customer)
            self.session.add(BillingEvent(event_id=event_id, event_type=kind, outcome=outcome))
            self.session.commit()
            if outcome.startswith("review_"):
                logger.warning("Billing review required (event_type=%s, reason=%s)", kind, outcome)
            return
        except IntegrityError:
            self.session.rollback()
            # Concurrent duplicate delivery: the winning transaction committed both.
            if self.session.get(BillingEvent, event_id) is not None:
                return
        except (SQLAlchemyError, stripe.error.StripeError, StripeWebhookProcessingError):
            self.session.rollback()
        # No raw payload, SQL parameters, provider messages, or exception chain.
        logger.error("Billing event processing requires retry (event_type=%s)", kind)
        raise StripeWebhookProcessingError("Billing state could not be synchronized; retry required") from None

    def _reconcile(self, user: User, customer: str) -> str:
        if not self.settings.is_configured:
            raise StripeWebhookProcessingError("Billing reconciliation is not configured")
        response = _plain(stripe.Subscription.list(
            customer=customer, status="all", limit=100, expand=["data.latest_invoice"],
            api_key=self.settings.stripe_secret_key, stripe_version=STRIPE_API_VERSION,
        ))
        # Never decide access from a truncated or malformed view.
        if response.get("has_more") or not isinstance(response.get("data"), list):
            raise StripeWebhookProcessingError("Incomplete subscription state")
        matches = []
        for subscription in response["data"]:
            subscription = _plain(subscription)
            if subscription.get("customer") != customer:
                continue
            items = (subscription.get("items") or {}).get("data") or []
            if any((item.get("price") or {}).get("id") == self.settings.stripe_price_id_pro for item in items):
                matches.append(subscription)
        if not matches:
            # Legacy/manual entitlements or a retired Price need review, not revocation.
            return "review_unmatched_price"

        def paid(subscription: dict) -> bool:
            invoice = subscription.get("latest_invoice")
            return isinstance(invoice, dict) and (invoice.get("paid") is True or invoice.get("status") == "paid")

        entitled = [s for s in matches if s.get("status") == "trialing" or (
            s.get("status") == "active" and paid(s)
        )]
        grace = [s for s in matches if s.get("status") == "past_due"]
        if entitled:
            selected = max(entitled, key=lambda s: self._period_end(s) or 0)
            user.subscription_tier = "pro"
        elif grace and user.subscription_tier == "pro":
            selected = max(grace, key=lambda s: self._period_end(s) or 0)
            # Keep existing access during retries; do not grant an unpaid first invoice.
        elif any(s.get("status") not in {"canceled", "unpaid", "incomplete_expired", "incomplete"} for s in matches):
            return "review_unsettled_subscription"
        elif any(s.get("status") == "incomplete" for s in matches):
            return "review_unsettled_subscription"
        else:
            # All matching subscriptions have authoritative terminal status.
            selected = max(matches, key=lambda s: s.get("created") or 0)
            user.subscription_tier = "free"
        user.subscription_status = selected["status"]
        user.cancel_at_period_end = bool(selected.get("cancel_at_period_end"))
        end = self._period_end(selected)
        if selected.get("status") == "canceled":
            end = selected.get("ended_at") or end
        user.subscription_ends_at = datetime.fromtimestamp(end, timezone.utc) if end else None
        return "reconciled"

    @staticmethod
    def _period_end(subscription: dict) -> int | None:
        periods = [item.get("current_period_end") for item in (subscription.get("items") or {}).get("data", [])]
        periods.append(subscription.get("current_period_end"))
        return max((value for value in periods if isinstance(value, int)), default=None)
