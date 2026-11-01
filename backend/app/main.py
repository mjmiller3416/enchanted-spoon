"""app/main.py

Main FastAPI application for Enchanted Spoon.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.observability import init_sentry
from app.core.rate_limit import limiter
from app.core.startup import validate_config
from app.database.db import SessionLocal
from app.services.free_tier_sunset import apply_free_tier_sunset
from app.router import api_router

logger = logging.getLogger(__name__)

# Before the app is built so Sentry's FastAPI integration can hook it
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate critical configuration before serving any requests."""
    validate_config()
    from app.core.offer_windows import log_legacy_cutoff_if_unset
    from app.services.household.usage_meter import install_household_usage_hooks

    install_household_usage_hooks()
    log_legacy_cutoff_if_unset()
    _apply_sunset_if_due()
    yield


def _apply_sunset_if_due() -> None:
    """Persist read-only once the configured free-plan date has passed."""
    from app.core.offer_windows import sunset_is_due

    if not sunset_is_due():
        return
    session = SessionLocal()
    try:
        apply_free_tier_sunset(session)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Free-tier sunset migration failed")
    finally:
        session.close()


# Create FastAPI app
app = FastAPI(
    title="Enchanted Spoon API",
    description="Backend API for the Enchanted Spoon recipe management and meal planning application",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting (slowapi) - see app/core/rate_limit.py for the shared Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Get allowed origins from environment or use wildcard for development.
# Whitespace is stripped so "a, b" parses into distinct origins.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

# The CORS spec forbids combining a wildcard origin with credentials. In that
# configuration Starlette reflects the caller's Origin back with
# allow_credentials=True — letting *any* site make credentialed requests. Only
# enable credentials when specific origins are configured.
allow_credentials = CORS_ORIGINS != ["*"]

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "Enchanted Spoon API is running",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Liveness plus the free-tier cutoff fail-safe.

    ``status`` stays ``healthy`` so a missing cutoff does not fail the
    process check. ``legacy_free_cutoff_configured`` is false, and
    ``legacy_free_cutoff_error`` is set, until the variable is present.
    """
    from app.core.offer_windows import legacy_cutoff_status

    body = {"status": "healthy"}
    body.update(legacy_cutoff_status())
    return body


# Optional: Serve static files for images if needed
# Uncomment and adjust path if you want to serve images from the backend
# static_path = Path(__file__).parent.parent / "static"
# if static_path.exists():
#     app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
