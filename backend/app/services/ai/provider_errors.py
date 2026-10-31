"""app/services/ai/provider_errors.py

Client-safe messages for failed Gemini calls.

Gemini's error text names billing, quotas and project settings (for example
"Your prepayment credits are depleted. Please go to AI Studio..."), so it must
never reach users. These helpers log the real error, with its traceback, and
hand back a message that is safe to show.
"""

import logging

from google.genai import errors as genai_errors

logger = logging.getLogger(__name__)

# Shown when the provider account or service is at fault, not the request
AI_UNAVAILABLE_MESSAGE = "AI features are temporarily unavailable. Please try again later."

# Shown for any other failure while serving an AI request
AI_FAILED_MESSAGE = "Something went wrong with that AI request. Please try again."

# 401/403: key rejected or revoked; 402: prepaid credits depleted;
# 429: quota or rate limit exhausted. Every user gets these until an admin acts.
_ACCOUNT_STATUS_CODES = frozenset({401, 402, 403, 429})

# ErrorInfo reason Gemini puts in a 400 response when the API key is invalid
_INVALID_KEY_REASON = "API_KEY_INVALID"


def is_provider_unavailable(exc: BaseException) -> bool:
    """Return True if a Gemini error means AI is down for everyone, not just this request.

    That covers account problems (billing, quota, a bad key) and Google-side
    outages (5xx). Request-level errors and our own bugs return False.
    """
    if not isinstance(exc, genai_errors.APIError):
        return False
    code = exc.code
    if code in _ACCOUNT_STATUS_CODES or (isinstance(code, int) and code >= 500):
        return True
    # Gemini answers an invalid or revoked key with 400, not 401
    return _INVALID_KEY_REASON in str(exc.details)


def safe_ai_error(exc: BaseException, feature: str) -> str:
    """Log a failed AI call and return a message that is safe to show users.

    Call from inside the ``except`` block that caught ``exc``. The log line
    carries the real error and traceback (and reaches Sentry when it's
    configured); the caller passes the returned message to the client.

    Args:
        exc: The exception raised while serving the AI request.
        feature: Short feature name for the log line, e.g. "Assistant".

    Returns:
        AI_UNAVAILABLE_MESSAGE when the provider account or service is at
        fault, otherwise AI_FAILED_MESSAGE.
    """
    logger.error("[%s] AI request failed: %s", feature, exc, exc_info=exc)
    if is_provider_unavailable(exc):
        return AI_UNAVAILABLE_MESSAGE
    return AI_FAILED_MESSAGE
