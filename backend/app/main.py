"""app/main.py

Main FastAPI application for Meal Genie.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.rate_limit import limiter
from app.core.startup import validate_config
from app.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate critical configuration before serving any requests."""
    validate_config()
    yield


# Create FastAPI app
app = FastAPI(
    title="Meal Genie API",
    description="Backend API for the Meal Genie recipe management and meal planning application",
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
        "message": "Meal Genie API is running",
        "version": "1.0.0",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Optional: Serve static files for images if needed
# Uncomment and adjust path if you want to serve images from the backend
# static_path = Path(__file__).parent.parent / "static"
# if static_path.exists():
#     app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
