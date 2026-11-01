"""app/core/stripe_config.py

Stripe billing configuration using pydantic-settings.
Manages API keys, the Pro subscription price ID, and redirect URLs
used by Checkout and the billing portal.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# SDK 16.0.0 and snapshot webhook fixtures are tested against this version.
STRIPE_API_VERSION = "2026-09-30.endive"
STRIPE_TRIAL_DAYS = 7


class StripeSettings(BaseSettings):
    """
    Stripe settings loaded from environment variables.

    Attributes:
        stripe_secret_key: Stripe secret key for API calls (sk_xxx)
        stripe_webhook_secret: Signing secret for verifying webhook events (whsec_xxx)
        stripe_price_id_pro: Price ID for the Pro subscription plan
        frontend_url: Base URL of the frontend app, used to build Checkout
            success/cancel URLs and the billing-portal return URL
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Explicit release gate; portal access and webhook processing remain available.
    stripe_checkout_enabled: bool = False
    stripe_secret_key: Optional[str] = Field(default=None, repr=False)
    stripe_webhook_secret: Optional[str] = Field(default=None, repr=False)
    stripe_price_id_pro: Optional[str] = None
    # Current prices. Monthly falls back to STRIPE_PRICE_ID_PRO when V2 is unset.
    stripe_price_pro_monthly_v2: Optional[str] = None
    stripe_price_pro_annual_v2: Optional[str] = None
    frontend_url: str = "http://localhost:3000"

    @property
    def monthly_price_id(self) -> Optional[str]:
        return self.stripe_price_pro_monthly_v2 or self.stripe_price_id_pro

    @property
    def annual_price_id(self) -> Optional[str]:
        return self.stripe_price_pro_annual_v2

    def pro_price_ids(self) -> set[str]:
        return {
            price
            for price in (
                self.monthly_price_id,
                self.annual_price_id,
                self.stripe_price_id_pro,
            )
            if price
        }

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is configured well enough to create checkout sessions."""
        return bool(self.stripe_secret_key and self.monthly_price_id)


@lru_cache()
def get_stripe_settings() -> StripeSettings:
    """
    Get cached Stripe settings instance.

    Uses lru_cache to ensure settings are loaded once and reused,
    avoiding repeated .env file reads.
    """
    return StripeSettings()
