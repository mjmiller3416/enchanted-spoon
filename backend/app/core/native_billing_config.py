"""Native in-app purchase configuration.

Store products are not created by this codebase. Product ids default to the
ids we will register in App Store Connect and Play Console. Purchases stay
off until ``NATIVE_IAP_ENABLED`` is true and RevenueCat credentials are set.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Keep in sync with frontend/src/lib/pro-plans.ts
PRO_MONTHLY_PRODUCT_ID = "com.enchantedspoon.app.pro.monthly"
PRO_ANNUAL_PRODUCT_ID = "com.enchantedspoon.app.pro.annual"
PRO_ENTITLEMENT_ID = "pro"


class NativeBillingSettings(BaseSettings):
    """Server-side switches for StoreKit / Play Billing via RevenueCat."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    native_iap_enabled: bool = False
    revenuecat_webhook_authorization: Optional[str] = None
    revenuecat_secret_api_key: Optional[str] = None
    iap_monthly_product_id: str = PRO_MONTHLY_PRODUCT_ID
    iap_annual_product_id: str = PRO_ANNUAL_PRODUCT_ID
    revenuecat_entitlement_id: str = PRO_ENTITLEMENT_ID

    @property
    def webhook_configured(self) -> bool:
        return bool(self.revenuecat_webhook_authorization)

    @property
    def api_configured(self) -> bool:
        return bool(self.revenuecat_secret_api_key)


@lru_cache()
def get_native_billing_settings() -> NativeBillingSettings:
    """Load native billing settings once per process."""
    return NativeBillingSettings()


def is_native_billing_client(client_header: Optional[str]) -> bool:
    """True when the web app is running inside the Capacitor shell.

    The shell sets ``X-Enchanted-Spoon-Client: native-ios`` or ``native-android``.
    Stripe Checkout and the billing portal are refused for those clients so
    the binary does not offer an external purchase flow.
    """
    if not client_header:
        return False
    return client_header.strip().lower().startswith("native")


def authorization_matches(header: Optional[str], expected: Optional[str]) -> bool:
    """Constant-time compare of a RevenueCat webhook Authorization header.

    Accepts the configured value as-is or with a ``Bearer `` prefix, since
    the dashboard lets you set either form.
    """
    if not header or not expected:
        return False
    candidates = [expected]
    if not expected.lower().startswith("bearer "):
        candidates.append(f"Bearer {expected}")
    else:
        candidates.append(expected[len("Bearer "):])
    presented = header.strip()
    return any(secrets.compare_digest(presented, candidate) for candidate in candidates)
