"""Shared Gemini client factory for AI services.

Provides a lazy-initialized client factory that eliminates the duplicated
client initialization pattern across individual AI services.
"""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Cache of initialized clients keyed by API key plus transport policy.
# Image calls must not share a text client's retry/timeout settings.
_clients: dict[tuple, object] = {}

# Bounded timeout for text Gemini calls, in milliseconds.
_REQUEST_TIMEOUT_MS = 60_000
_IMAGE_TIMEOUT_MS = 120_000

# Text: one retry (attempts=2 means the first try plus one retry) and only
# for throttling or temporary unavailability. 500 is not retried.
_RETRY_ATTEMPTS = 2
_RETRY_INITIAL_DELAY_SECONDS = 1.0
_RETRY_MAX_DELAY_SECONDS = 10.0
_RETRY_EXP_BASE = 2.0
_RETRY_HTTP_STATUS_CODES = [429, 503]


def get_gemini_client(
    api_key_env: str,
    fallback_env: Optional[str] = None,
    *,
    retry_attempts: Optional[int] = None,
    timeout_ms: Optional[int] = None,
) -> object:
    """Get a lazily-initialized Gemini client for the given API key env var.

    Args:
        api_key_env: Primary environment variable name for the API key.
        fallback_env: Optional fallback environment variable if primary is unset.
        retry_attempts: Total SDK attempts. Text defaults to 2. Image calls pass 1
            so a simulated 500 is exactly one provider request.
        timeout_ms: Request timeout. Image calls pass 120000.

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

    attempts = _RETRY_ATTEMPTS if retry_attempts is None else retry_attempts
    timeout = _REQUEST_TIMEOUT_MS if timeout_ms is None else timeout_ms
    cache_key = (api_key, attempts, timeout, tuple(_RETRY_HTTP_STATUS_CODES))

    if cache_key not in _clients:
        from google import genai
        from google.genai import types

        http_options = types.HttpOptions(
            timeout=timeout,
            retry_options=types.HttpRetryOptions(
                attempts=attempts,
                initial_delay=_RETRY_INITIAL_DELAY_SECONDS,
                max_delay=_RETRY_MAX_DELAY_SECONDS,
                exp_base=_RETRY_EXP_BASE,
                http_status_codes=list(_RETRY_HTTP_STATUS_CODES),
            ),
        )
        _clients[cache_key] = genai.Client(api_key=api_key, http_options=http_options)

    return _clients[cache_key]


def clear_gemini_clients() -> None:
    """Drop cached clients. Tests use this after changing env or retry policy."""
    _clients.clear()
