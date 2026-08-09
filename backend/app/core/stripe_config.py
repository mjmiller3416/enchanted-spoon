"""app/core/stripe_config.py

Stripe billing configuration using pydantic-settings.
Manages API keys, the Pro subscription price ID, and redirect URLs
used by Checkout and the billing portal.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_id_pro: Optional[str] = None
    frontend_url: str = "http://localhost:3000"

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is configured well enough to create checkout sessions."""
        return bool(self.stripe_secret_key and self.stripe_price_id_pro)


@lru_cache()
def get_stripe_settings() -> StripeSettings:
    """
    Get cached Stripe settings instance.

    Uses lru_cache to ensure settings are loaded once and reused,
    avoiding repeated .env file reads.
    """
    return StripeSettings()
