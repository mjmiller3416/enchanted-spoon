"""app/api/auth/dependencies.py

FastAPI dependencies for authentication and authorization.
Provides get_current_user and related dependencies for protecting routes.
"""

import logging
from typing import Callable, Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ...core.auth_config import AuthSettings, get_auth_settings
from ...core.usage_limits import get_monthly_limit
from ...database.db import get_session
from ...models.user import User
from ...services.usage_service import UsageLimitExceededError, UsageService
from ...services.user_service import AccountLinkError, UserService
from .jwks import get_clerk_jwks, _get_signing_key

logger = logging.getLogger(__name__)

# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)


def _email_from_claims(payload: dict) -> Optional[str]:
    """First usable email claim; tolerant of missing/empty/malformed fields."""
    for key in ("email", "primary_email_address"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    addresses = payload.get("email_addresses")
    if isinstance(addresses, list):
        for entry in addresses:
            if isinstance(entry, dict) and isinstance(entry.get("email_address"), str):
                return entry["email_address"].strip() or None
    return None


# ── Authentication Dependencies ─────────────────────────────────────────────


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    """
    Dependency to get the currently authenticated user.

    Flow:
    1. If auth_disabled, return dev user (for local development)
    2. Extract and validate Bearer token
    3. Decode JWT using Clerk's JWKS
    4. Look up or create user from token claims

    Usage:
        @router.get("/me")
        def get_profile(current_user: User = Depends(get_current_user)):
            return current_user

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException 401: Missing or invalid token.
        HTTPException 500: Dev user not found (only in dev mode).
    """
    # Debug: Print auth state
    logger.debug(f"Auth disabled={settings.auth_disabled}, has credentials={credentials is not None}")

    # Dev mode bypass - return configured dev user
    if settings.auth_disabled:
        logger.debug("Dev mode - bypassing authentication")
        user_service = UserService(session)
        dev_user = user_service.get_by_id(settings.dev_user_id)
        if not dev_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Dev user with id={settings.dev_user_id} not found. "
                f"Run migrations and seed data first.",
            )
        return dev_user

    # Require token in production mode
    if not credentials:
        logger.debug("No credentials provided - returning 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    logger.debug(f"Token received, length={len(token)}")

    # Get JWKS and find matching signing key
    logger.debug("Fetching JWKS...")
    jwks = await get_clerk_jwks(settings)
    logger.debug(f"Got JWKS with {len(jwks.get('keys', []))} keys")

    signing_key = _get_signing_key(jwks, token)
    logger.debug(f"Found signing key: kid={signing_key.get('kid', 'unknown')}")

    # Decode and verify JWT
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Clerk doesn't always set aud
                "verify_iss": False,  # We trust Clerk's signature
            },
        )
        logger.debug(f"JWT decoded successfully, sub={payload.get('sub', 'unknown')}")
    except JWTError as e:
        logger.error(f"JWT decode failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract claims from JWT
    # Clerk JWTs use 'sub' for user ID, and may include email in different fields
    logger.debug(f"JWT payload keys: {list(payload.keys())}")
    clerk_id = payload.get("sub")
    email = _email_from_claims(payload)
    name = payload.get("name") or payload.get("first_name")
    avatar_url = payload.get("picture") or payload.get("image_url")
    logger.debug(f"Extracted: clerk_id={clerk_id}, email={email}, name={name}")

    if not clerk_id:
        logger.error("Missing clerk_id (sub claim)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claim: sub",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not email:
        # Never log the payload itself: it carries the user's personal data
        logger.error("Missing email - JWT does not contain email claim (keys: %s)", sorted(payload))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claim: email",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get or create user from token claims
    user_service = UserService(session)
    try:
        user = user_service.get_or_create_from_clerk(
            clerk_id=clerk_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
    except AccountLinkError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "An Enchanted Spoon account already uses this email address, but it "
                "couldn't be linked to this sign-in. Please verify your email address "
                "or contact support."
            ),
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_session),
    settings: AuthSettings = Depends(get_auth_settings),
) -> Optional[User]:
    """
    Like get_current_user, but returns None instead of raising 401.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    For example, a recipe list might show public recipes to everyone but
    include user's private recipes only when authenticated.

    Usage:
        @router.get("/recipes")
        def list_recipes(current_user: Optional[User] = Depends(get_current_user_optional)):
            if current_user:
                # Include user's private recipes
                ...
            else:
                # Public recipes only
                ...

    Returns:
        User if authenticated, None otherwise.
    """
    if not credentials and not settings.auth_disabled:
        return None

    try:
        return await get_current_user(credentials, session, settings)
    except HTTPException:
        return None


def require_pro(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires pro-level access.

    Checks the user's has_pro_access property, which considers:
    - Admin status (permanent access)
    - Active paid subscription
    - Temporary granted access (testers/promos)

    Usage:
        @router.post("/ai/generate-image")
        def generate_image(current_user: User = Depends(require_pro)):
            # Only pro users can access this
            ...

    Returns:
        User: The authenticated user with pro access.

    Raises:
        HTTPException 403: User doesn't have pro access.
    """
    if not user.has_pro_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro subscription required for this feature",
        )
    return user


def require_within_usage_limit(field: str) -> Callable[..., Generator[User, None, None]]:
    """
    Dependency factory that enforces a monthly usage cap for a Gemini-backed
    AI feature, resolved from the user's subscription tier.

    Reserves one unit of `field` against the user's tier cap in
    `app/core/usage_limits.py` before the route runs (one atomic conditional
    UPDATE, so parallel requests can't overshoot the cap), and refunds it if
    the route raises. Routes therefore must not increment `field` themselves.
    Admins are uncapped but still counted. Free users are metered (a small
    taste-test allowance), not blocked outright — the binary `require_pro`
    gate was deliberately dropped here when the metered free tier landed
    (#164), so a capped free user gets a structured 429 the frontend can turn
    into an upgrade prompt.

    Usage:
        @router.post("/ai/generate-image")
        def generate_image(
            current_user: User = Depends(require_within_usage_limit("ai_images_generated")),
        ):
            # Any authenticated user under their tier's monthly cap
            ...

    Returns:
        A dependency callable resolving to the authenticated User.

    Raises:
        HTTPException 429: User has reached their tier's monthly cap for `field`.
    """

    def _reserve_usage(
        user: User = Depends(get_current_user),
        session: Session = Depends(get_session),
    ) -> Generator[User, None, None]:
        if user.is_admin:
            limit = None
        else:
            tier = "pro" if user.has_pro_access else "free"
            limit = get_monthly_limit(tier, field)

        usage_service = UsageService(session, user.id)
        try:
            usage_service.reserve(field, limit)
        except UsageLimitExceededError as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "usage_limit_exceeded",
                    "field": e.field,
                    "current": e.current,
                    "limit": e.limit,
                    "message": (
                        f"Monthly limit reached for this feature "
                        f"({e.current}/{e.limit}). Resets at the start of next month."
                    ),
                },
            )

        try:
            yield user
        except Exception:
            # The feature failed — don't charge the user for it
            try:
                usage_service.release(field)
            except Exception:
                logger.exception("Failed to refund %s usage for user %s", field, user.id)
            raise

    return _reserve_usage


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires admin-level access.

    Checks the user's is_admin flag for permanent admin access.

    Usage:
        @router.get("/admin/users")
        def list_users(current_admin: User = Depends(require_admin)):
            # Only admins can access this
            ...

    Returns:
        User: The authenticated admin user.

    Raises:
        HTTPException 403: User is not an admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this feature",
        )
    return user
