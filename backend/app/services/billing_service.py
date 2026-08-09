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

from ..core.stripe_config import StripeSettings, get_stripe_settings
from ..models.user import User
from ..repositories.user_repo import UserRepo

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
        if user.stripe_customer_id:
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

    def create_checkout_session(self, user: User) -> str:
        """
        Create a Stripe Checkout session for the Pro subscription.

        Creates the Stripe customer first if the user doesn't have one yet.

        Args:
            user: The authenticated user.

        Returns:
            The Checkout session redirect URL.

        Raises:
            StripeNotConfiguredError: Stripe secret key or price ID is not set.
            StripeCustomerError: Customer creation failed.
            CheckoutSessionError: Checkout session creation failed.
        """
        self._require_configured()
        customer_id = self.get_or_create_customer(user)

        try:
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": self.settings.stripe_price_id_pro, "quantity": 1}],
                success_url=f"{self.settings.frontend_url}/settings?checkout=success",
                cancel_url=f"{self.settings.frontend_url}/settings?checkout=cancelled",
                client_reference_id=str(user.id),
            )
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
