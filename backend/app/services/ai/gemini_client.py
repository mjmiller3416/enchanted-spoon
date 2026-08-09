"""Shared Gemini client factory for AI services.

Provides a lazy-initialized client factory that eliminates the duplicated
client initialization pattern across individual AI services.
"""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Cache of initialized clients keyed by resolved API key
_clients: dict[str, object] = {}

# Bounded timeout for every Gemini API call, in milliseconds. The SDK's
# default has no timeout, so a stalled request would otherwise hang forever.
_REQUEST_TIMEOUT_MS = 60_000

# Retry transient failures (rate limiting and server errors) with capped
# exponential backoff. The SDK's default is to never retry.
_RETRY_ATTEMPTS = 3
_RETRY_INITIAL_DELAY_SECONDS = 1.0
_RETRY_MAX_DELAY_SECONDS = 10.0
_RETRY_EXP_BASE = 2.0
_RETRY_HTTP_STATUS_CODES = [429, 500, 502, 503, 504]


def get_gemini_client(api_key_env: str, fallback_env: Optional[str] = None) -> object:
    """Get a lazily-initialized Gemini client for the given API key env var.

    Args:
        api_key_env: Primary environment variable name for the API key.
        fallback_env: Optional fallback environment variable if primary is unset.

    Returns:
        A google.genai.Client instance.

    Raises:
        ValueError: If no API key is found in any of the specified env vars.
    """
    api_key = os.getenv(api_key_env)
    if not api_key and fallback_env:
        api_key = os.getenv(fallback_env)

    if not api_key:
        env_names = api_key_env if not fallback_env else f"{api_key_env} or {fallback_env}"
        raise ValueError(f"API key not found. Set {env_names}.")

    if api_key not in _clients:
        from google import genai
        from google.genai import types

        http_options = types.HttpOptions(
            timeout=_REQUEST_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(
                attempts=_RETRY_ATTEMPTS,
                initial_delay=_RETRY_INITIAL_DELAY_SECONDS,
                max_delay=_RETRY_MAX_DELAY_SECONDS,
                exp_base=_RETRY_EXP_BASE,
                http_status_codes=_RETRY_HTTP_STATUS_CODES,
            ),
        )
        _clients[api_key] = genai.Client(api_key=api_key, http_options=http_options)

    return _clients[api_key]
