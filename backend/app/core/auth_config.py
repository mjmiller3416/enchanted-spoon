"""app/core/auth_config.py

Authentication configuration using pydantic-settings.
Manages Clerk JWT validation settings and development mode bypass.
"""

import base64
import logging
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class AuthSettings(BaseSettings):
    """
    Authentication settings loaded from environment variables.

    Attributes:
        clerk_secret_key: Clerk secret key for API calls (sk_xxx)
        CLERK_PUBLISHABLE_KEY: Clerk publishable key (pk_xxx)
        clerk_jwks_url: Optional explicit JWKS URL override (derived from publishable key if not set)
        auth_disabled: When True, bypasses JWT validation outside production (local dev)
        dev_user_id: User ID to use when auth_disabled is True
        integration_api_key: Shared secret for trusted first-party app-to-app calls
            (checked against the X-API-Key header on integration endpoints)
        integration_user_id: User whose data integration pushes are written to
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Clerk configuration
    clerk_secret_key: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    clerk_jwks_url: Optional[str] = None  # Explicit override; derived from publishable key if not set

    # Development mode bypass
    auth_disabled: bool = False
    dev_user_id: int = 1

    # First-party integration (app-to-app) auth
    integration_api_key: Optional[str] = None
    integration_user_id: Optional[int] = None

    @property
    def is_configured(self) -> bool:
        """Check if Clerk is properly configured for production use."""
        return bool(self.clerk_secret_key and self.CLERK_PUBLISHABLE_KEY)

    @property
    def derived_jwks_url(self) -> Optional[str]:
        """
        Derive the JWKS URL from the Clerk publishable key.

        Clerk publishable keys encode the frontend API host in base64:
        - pk_test_<base64>$ or pk_live_<base64>$
        - The base64 portion decodes to the frontend API hostname
        - JWKS is served at https://{host}/.well-known/jwks.json

        Returns:
            The derived JWKS URL, or None if publishable key is missing/invalid.
        """
        if not self.CLERK_PUBLISHABLE_KEY:
            return None

        try:
            # Extract the base64 portion after pk_test_ or pk_live_
            # Format: pk_test_<base64>$ or pk_live_<base64>$
            key = self.CLERK_PUBLISHABLE_KEY
            if key.startswith("pk_test_"):
                encoded = key[8:]  # Remove "pk_test_"
            elif key.startswith("pk_live_"):
                encoded = key[8:]  # Remove "pk_live_"
            else:
                logger.warning(f"Unexpected publishable key format: {key[:15]}...")
                return None

            # Remove trailing $ if present
            if encoded.endswith("$"):
                encoded = encoded[:-1]

            # Decode base64 to get the frontend API host
            # Add padding if needed (base64 requires length divisible by 4)
            padding_needed = 4 - (len(encoded) % 4)
            if padding_needed != 4:
                encoded += "=" * padding_needed

            frontend_api_host = base64.b64decode(encoded).decode("utf-8")
            # Clerk encodes a trailing $ in the hostname as a delimiter - strip it
            frontend_api_host = frontend_api_host.rstrip("$")
            jwks_url = f"https://{frontend_api_host}/.well-known/jwks.json"
            logger.debug(f"Derived JWKS URL from publishable key: {jwks_url}")
            return jwks_url

        except Exception as e:
            logger.error(f"Failed to derive JWKS URL from publishable key: {e}")
            return None

    @property
    def effective_jwks_url(self) -> Optional[str]:
        """
        Get the JWKS URL to use for JWT verification.

        Priority:
        1. Explicit clerk_jwks_url env var (for manual override)
        2. Derived from CLERK_PUBLISHABLE_KEY

        Returns:
            The JWKS URL to use, or None if neither is available.
        """
        if self.clerk_jwks_url:
            logger.debug(f"Using explicit JWKS URL: {self.clerk_jwks_url}")
            return self.clerk_jwks_url
        return self.derived_jwks_url


@lru_cache()
def get_auth_settings() -> AuthSettings:
    """
    Get cached auth settings instance.

    Uses lru_cache to ensure settings are loaded once and reused,
    avoiding repeated .env file reads.
    """
    return AuthSettings()
