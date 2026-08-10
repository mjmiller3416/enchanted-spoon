"""app/core/startup.py

Startup configuration validation.

Fails fast when a production deployment is missing critical configuration,
rather than silently falling back to insecure development defaults (an open
auth bypass, or a throwaway SQLite file that discards every write on redeploy).

"Production" is signalled by the ``ENVIRONMENT`` env var. Anything other than
``production`` (the default is ``development``) is treated as a dev/test
environment, where the same problems are logged as informational notices
instead of aborting startup.
"""

import logging
import os

from app.core.auth_config import get_auth_settings
from app.database.db import SQLALCHEMY_DATABASE_URL

logger = logging.getLogger(__name__)


class ConfigError(RuntimeError):
    """Raised when required production configuration is missing or unsafe."""


def is_production() -> bool:
    """Return True when running in a production-looking environment."""
    return os.environ.get("ENVIRONMENT", "development").strip().lower() == "production"


def _uses_sqlite() -> bool:
    return SQLALCHEMY_DATABASE_URL.startswith("sqlite")


def validate_config() -> None:
    """Validate critical configuration, aborting startup in production if unsafe.

    Raises:
        ConfigError: In production, if auth is bypassed/unconfigured or the
            database is still pointed at SQLite.
    """
    auth = get_auth_settings()
    production = is_production()

    if not production:
        # Dev/test: surface the state without blocking startup.
        if auth.auth_disabled:
            logger.info(
                "Auth is disabled for local development (DEV_USER_ID=%s).",
                auth.dev_user_id,
            )
        if _uses_sqlite():
            logger.info("Using SQLite database for local development.")
        return

    problems: list[str] = []

    if auth.auth_disabled:
        problems.append(
            "AUTH_DISABLED is true in a production environment — refusing to run "
            "with authentication bypassed."
        )
    if not auth.is_configured:
        problems.append(
            "Clerk is not configured (CLERK_SECRET_KEY / CLERK_PUBLISHABLE_KEY "
            "missing) — JWT validation cannot work."
        )
    if _uses_sqlite():
        problems.append(
            "SQLALCHEMY_DATABASE_URL points at SQLite in production — set the "
            "Postgres connection string."
        )

    if problems:
        for problem in problems:
            logger.critical("Startup config error: %s", problem)
        raise ConfigError(
            "Refusing to start with invalid production configuration:\n  - "
            + "\n  - ".join(problems)
        )

    logger.info(
        "Config validated (environment=production, auth_configured=%s, db=%s).",
        auth.is_configured,
        "sqlite" if _uses_sqlite() else "postgres",
    )
