"""app/services/billing_service.py

Service layer for Stripe billing: customer creation, Checkout session
creation, and billing-portal session creation.

This covers only the outbound/checkout half of billing. Subscription
state itself (tier, status, renewal date) is written by the Stripe
webhook handler, tracked separately.
"""

from __future__ import annotations

import logging

import stripe
from sqlalchemy.orm import Session

from ..core.stripe_config import STRIPE_API_VERSION, STRIPE_TRIAL_DAYS, StripeSettings, get_stripe_settings
from ..models.user import User
from ..repositories.user_repo import UserRepo
from .founder_codes import PromotionCodeRejected, lookup_founder_promotion, normalize_founder_code

logger = logging.getLogger(__name__)


class StripeNotConfiguredError(Exception):
    """Raised when required Stripe environment variables are missing."""


class StripeCustomerError(Exception):
    """Raised when creating or retrieving a Stripe customer fails."""


class CheckoutSessionError(Exception):
    """Raised when creating a Stripe Checkout session fails."""


class PortalSessionError(Exception):
    """Raised when creating a Stripe billing-portal session fails."""


class BillingService:
    """Service layer for Stripe billing operations."""

    def __init__(self, session: Session, settings: StripeSettings | None = None):
        self.session = session
        self.repo = UserRepo(session)
        self.settings = settings or get_stripe_settings()
        if self.settings.stripe_secret_key:
            stripe.api_key = self.settings.stripe_secret_key
            stripe.api_version = STRIPE_API_VERSION

    def _require_configured(self) -> None:
        if not self.settings.is_configured:
            raise StripeNotConfiguredError(
                "Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID_PRO."
            )

    def get_or_create_customer(self, user: User) -> str:
        """
        Return the user's Stripe customer ID, creating one on first use.

        Args:
            user: The authenticated user.

        Returns:
            The Stripe customer ID (cus_xxx).

        Raises:
            StripeNotConfiguredError: Stripe secret key is not set.
            StripeCustomerError: Stripe API call failed.
        """
        if user.stripe_customer_id and not self._customer_has_invoice(user.stripe_customer_id):
            return user.stripe_customer_id

        self._require_configured()
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name or None,
                metadata={"user_id": str(user.id)},
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed for user {user.id}: {e}")
            raise StripeCustomerError("Failed to create Stripe customer.") from e

        self.repo.set_stripe_customer_id(user, customer.id)
        self.session.commit()
        return customer.id

    def _customer_has_invoice(self, customer_id: str) -> bool:
        """True when this Stripe customer already has any invoice.

        Those customers are not reused. A later checkout gets a new customer
        so a first-time-customer promotion is not evaluated against old invoices.
        """
        try:
            listed = stripe.Invoice.list(customer=customer_id, limit=1)
        except stripe.error.StripeError as e:
            logger.error("Stripe invoice lookup failed for customer %s", customer_id)
            raise StripeCustomerError("Failed to look up billing history.") from e
        data = listed.data if hasattr(listed, "data") else listed.get("data", [])
        return bool(data)

    def delete_customer(self, user: User) -> None:
        """
        Delete the user's Stripe customer, which immediately cancels any
        subscription so a deleted account is never billed again.

        No-op when the user never became a Stripe customer. A customer Stripe
        no longer has counts as deleted.

        Raises:
            StripeNotConfiguredError: The user has a customer but Stripe isn't configured.
            StripeCustomerError: Stripe API call failed.
        """
        if not user.stripe_customer_id:
            return
        if not self.settings.stripe_secret_key:
            raise StripeNotConfiguredError("Stripe is not configured; cannot cancel billing.")
        try:
            stripe.Customer.delete(user.stripe_customer_id)
        except stripe.error.InvalidRequestError as e:
            if getattr(e, "code", None) != "resource_missing":
                logger.error(f"Stripe customer delete failed for user {user.id}: {e}")
                raise StripeCustomerError("Failed to cancel billing.") from e
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer delete failed for user {user.id}: {e}")
            raise StripeCustomerError("Failed to cancel billing.") from e

    def create_checkout_session(
        self,
        user: User,
        plan: str = "monthly",
        promotion_code: str | None = None,
    ) -> str:
        """
        Create a Stripe Checkout session for monthly or annual Pro.

        Card is required (Checkout's default collection). A first subscription
        includes a 7-day trial. The founding code, when present, is attached
        as ``discounts=[{promotion_code}]`` and is not typed into Stripe's
        own promotion-code box. Tax is calculated by Stripe Tax; prices stay
        tax-exclusive.
        """
        if plan not in ("monthly", "annual"):
            raise CheckoutSessionError("Choose the monthly or annual plan.")
        if not self.settings.stripe_checkout_enabled:
            raise StripeNotConfiguredError("New subscriptions are not available yet. Please try again later.")
        self._require_configured()
        from app.core.startup import is_production

        if is_production() and (
            not (self.settings.stripe_secret_key or "").startswith(("sk_live_", "rk_live_"))
            or not self.settings.stripe_webhook_secret
            or not self.settings.frontend_url.startswith("https://")
        ):
            raise StripeNotConfiguredError("Paid checkout is not ready. Please contact support.")

        if plan == "annual":
            price_id = self.settings.annual_price_id
            if not price_id:
                raise StripeNotConfiguredError(
                    "Annual billing is not configured. Set STRIPE_PRICE_PRO_ANNUAL_V2."
                )
        else:
            price_id = self.settings.monthly_price_id
            if not price_id:
                raise StripeNotConfiguredError(
                    "Monthly billing is not configured. Set STRIPE_PRICE_PRO_MONTHLY_V2 or STRIPE_PRICE_ID_PRO."
                )

        code = normalize_founder_code(promotion_code)
        if code and user.has_used_trial:
            raise PromotionCodeRejected("Founding codes are for first-time customers.")
        promotion_id = lookup_founder_promotion(code, plan) if code else None

        customer_id = self.get_or_create_customer(user)
        params: dict = {
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{self.settings.frontend_url}/settings?checkout=success",
            "cancel_url": f"{self.settings.frontend_url}/settings?checkout=cancelled",
            "client_reference_id": str(user.id),
            "automatic_tax": {"enabled": True},
            "billing_address_collection": "required",
            "customer_update": {"address": "auto"},
        }
        if not user.has_used_trial:
            params["subscription_data"] = {
                "trial_period_days": STRIPE_TRIAL_DAYS,
                "trial_settings": {"end_behavior": {"missing_payment_method": "cancel"}},
            }
        if promotion_id:
            params["discounts"] = [{"promotion_code": promotion_id}]
            params.setdefault("subscription_data", {})["metadata"] = {"founder_code": code}

        try:
            checkout_session = stripe.checkout.Session.create(**params)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe checkout session creation failed for user {user.id}: {e}")
            raise CheckoutSessionError("Failed to create checkout session.") from e

        if not checkout_session.url:
            raise CheckoutSessionError("Stripe did not return a checkout URL.")
        return checkout_session.url

    def create_portal_session(self, user: User) -> str:
        """
        Create a Stripe billing-portal session for managing or cancelling
        the user's subscription.

        Args:
            user: The authenticated user.

        Returns:
            The billing-portal session URL.

        Raises:
            StripeNotConfiguredError: Stripe secret key is not set.
            PortalSessionError: User has no Stripe customer yet, or the
                Stripe API call failed.
        """
        self._require_configured()
        if not user.stripe_customer_id:
            raise PortalSessionError(
                "No billing account found for this user. Subscribe first to manage billing."
            )

        try:
            portal_session = stripe.billing_portal.Session.create(
                customer=user.stripe_customer_id,
                return_url=f"{self.settings.frontend_url}/settings",
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe portal session creation failed for user {user.id}: {e}")
            raise PortalSessionError("Failed to create billing portal session.") from e

        return portal_session.url
