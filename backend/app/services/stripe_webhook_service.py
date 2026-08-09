"""app/services/stripe_webhook_service.py

Service layer for processing signature-verified Stripe webhook events.
Syncs subscription state (tier, status, renewal date, customer id) onto
the matching User whenever Stripe reports a checkout or subscription change.
"""

# -- Imports -------------------------------------------------------------------------------------
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import stripe
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.stripe_config import StripeSettings
from ..models.user import ACTIVE_SUBSCRIPTION_STATUSES, User
from ..repositories.user_repo import UserRepo

logger = logging.getLogger(__name__)


# -- Exceptions ----------------------------------------------------------------------------------
class InvalidStripeSignatureError(Exception):
    """Raised when a webhook payload's Stripe-Signature cannot be verified."""
    pass


class StripeWebhookProcessingError(Exception):
    """Raised when a verified Stripe event cannot be processed."""
    pass


# -- Constants -------------------------------------------------------------------------------------
HANDLED_EVENT_TYPES = {
    "checkout.session.completed",
    "invoice.paid",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


# -- StripeWebhook Service -------------------------------------------------------------------------
class StripeWebhookService:
    """Verifies and applies Stripe webhook events to user subscription state."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = UserRepo(session)

    # -- Verification ------------------------------------------------------------------------
    def verify_and_parse_event(
        self,
        payload: bytes,
        signature: Optional[str],
        settings: StripeSettings,
    ) -> stripe.Event:
        """
        Verify a webhook payload's signature and parse it into a Stripe Event.

        Args:
            payload: Raw request body bytes (must be unparsed - signature covers exact bytes).
            signature: The `Stripe-Signature` header value.
            settings: Stripe settings holding the webhook signing secret.

        Returns:
            The verified Stripe Event.

        Raises:
            InvalidStripeSignatureError: If the signature is missing, malformed, or invalid,
                or if the webhook secret is not configured.
        """
        if not settings.stripe_webhook_secret:
            raise InvalidStripeSignatureError("Stripe webhook secret is not configured")
        if not signature:
            raise InvalidStripeSignatureError("Missing Stripe-Signature header")

        try:
            return stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )
        except ValueError as e:
            raise InvalidStripeSignatureError(f"Invalid webhook payload: {e}")
        except stripe.error.SignatureVerificationError as e:
            raise InvalidStripeSignatureError(f"Invalid webhook signature: {e}")

    # -- Event Handling ----------------------------------------------------------------------
    def handle_event(self, event: stripe.Event) -> None:
        """
        Apply a verified Stripe event to the matching user's subscription state.

        Unrecognized event types are ignored (Stripe sends far more event types
        than we care about). Events referencing a customer we can't resolve to a
        user are logged and skipped rather than raising, since Stripe will retry
        on non-2xx responses and there's nothing a retry could fix here.

        All handlers are idempotent upserts (they always write the event's
        current state), so redelivery of the same event is safe.

        Raises:
            StripeWebhookProcessingError: If a DB error occurs while applying the event.
        """
        event_type = event["type"]
        if event_type not in HANDLED_EVENT_TYPES:
            return

        data = event["data"]["object"]

        try:
            if event_type == "checkout.session.completed":
                self._handle_checkout_completed(data)
            elif event_type == "invoice.paid":
                self._handle_invoice_paid(data)
            elif event_type == "customer.subscription.updated":
                self._handle_subscription_updated(data)
            elif event_type == "customer.subscription.deleted":
                self._handle_subscription_deleted(data)
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise StripeWebhookProcessingError(
                f"Failed to process Stripe event '{event_type}': {e}"
            )

    # -- Handlers ------------------------------------------------------------------------------
    def _handle_checkout_completed(self, checkout_session: Mapping[str, Any]) -> None:
        customer_id = checkout_session.get("customer")
        client_reference_id = checkout_session.get("client_reference_id")

        user = self._resolve_user(client_reference_id, customer_id)
        if user is None:
            logger.warning(
                "checkout.session.completed: no matching user for "
                "client_reference_id=%s customer=%s",
                client_reference_id, customer_id,
            )
            return

        self.repo.update_subscription(
            user,
            stripe_customer_id=customer_id,
            subscription_tier="pro",
            subscription_status="active",
        )

    def _handle_invoice_paid(self, invoice: Mapping[str, Any]) -> None:
        user = self._get_user_by_customer_id(invoice.get("customer"))
        if user is None:
            return

        self.repo.update_subscription(
            user,
            subscription_tier="pro",
            subscription_status="active",
        )

    def _handle_subscription_updated(self, subscription: Mapping[str, Any]) -> None:
        user = self._get_user_by_customer_id(subscription.get("customer"))
        if user is None:
            return

        status = subscription.get("status", "active")
        tier = "pro" if status in ACTIVE_SUBSCRIPTION_STATUSES else "free"

        self.repo.update_subscription(
            user,
            subscription_tier=tier,
            subscription_status=status,
            subscription_ends_at=self._to_datetime(subscription.get("current_period_end")),
        )

    def _handle_subscription_deleted(self, subscription: Mapping[str, Any]) -> None:
        user = self._get_user_by_customer_id(subscription.get("customer"))
        if user is None:
            return

        ended_at = self._to_datetime(subscription.get("ended_at")) or datetime.now(timezone.utc)

        self.repo.update_subscription(
            user,
            subscription_tier="free",
            subscription_status="canceled",
            subscription_ends_at=ended_at,
        )

    # -- Helpers ------------------------------------------------------------------------------
    def _resolve_user(
        self, client_reference_id: Optional[str], customer_id: Optional[str]
    ) -> Optional[User]:
        if client_reference_id:
            try:
                user = self.repo.get_by_id(int(client_reference_id))
            except (TypeError, ValueError):
                user = None
            if user is not None:
                return user
        return self._get_user_by_customer_id(customer_id)

    def _get_user_by_customer_id(self, customer_id: Optional[str]) -> Optional[User]:
        if not customer_id:
            return None
        user = self.repo.get_by_stripe_customer_id(customer_id)
        if user is None:
            logger.warning("Stripe event referenced unknown customer_id=%s", customer_id)
        return user

    @staticmethod
    def _to_datetime(unix_timestamp: Optional[int]) -> Optional[datetime]:
        if unix_timestamp is None:
            return None
        return datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
