"""app/core/stripe_config.py

Stripe configuration using pydantic-settings.
Manages the API secret key and webhook signing secret.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class StripeSettings(BaseSettings):
    """
    Stripe settings loaded from environment variables.

    Attributes:
        stripe_secret_key: Stripe API secret key (sk_xxx) for server-side API calls
        stripe_webhook_secret: Signing secret (whsec_xxx) used to verify webhook payloads
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    @property
    def is_configured(self) -> bool:
        """Check if Stripe is properly configured to verify webhooks."""
        return bool(self.stripe_webhook_secret)


@lru_cache()
def get_stripe_settings() -> StripeSettings:
    """
    Get cached Stripe settings instance.

    Uses lru_cache to ensure settings are loaded once and reused,
    avoiding repeated .env file reads.
    """
    return StripeSettings()
