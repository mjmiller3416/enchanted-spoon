"""app/core/observability.py

Error reporting via Sentry (or any Sentry-compatible service, e.g. GlitchTip).

Disabled unless ``SENTRY_DSN`` is set, so local dev and tests send nothing.
Events carry only the internal user id — no emails, auth headers, IPs or
request bodies.
"""

import logging
import os
from typing import Any, Optional

import sentry_sdk

logger = logging.getLogger(__name__)

# Set on HTTPExceptions whose underlying error was already logged (and so
# already sent to Sentry with its real traceback) — see app/api/errors.py
REPORTED_ATTR = "_reported_to_sentry"


def _before_send(event: dict, hint: dict) -> Optional[dict]:
    """Drop the generic 500 that follows an error we already reported."""
    exc_info = hint.get("exc_info")
    if exc_info and getattr(exc_info[1], REPORTED_ATTR, False):
        return None
    return event


def init_sentry() -> bool:
    """Initialize Sentry if configured. Returns True when reporting is on."""
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=(
            os.environ.get("SENTRY_ENVIRONMENT")
            or os.environ.get("RAILWAY_ENVIRONMENT_NAME")
            or "development"
        ),
        # Railway injects the deployed commit, so every event names its build
        release=os.environ.get("RAILWAY_GIT_COMMIT_SHA") or None,
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0")),
        before_send=_before_send,
    )
    logger.info("Sentry error reporting enabled.")
    return True


def set_user(user_id: Any) -> None:
    """Tag this request's events with the internal user id (never email)."""
    sentry_sdk.set_user({"id": str(user_id)})
