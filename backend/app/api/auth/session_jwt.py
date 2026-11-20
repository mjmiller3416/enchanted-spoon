"""Verify a Clerk session JWT with the same JWKS path as the API.

The native sign-in ticket exchange only needs the Clerk user id and session
id. It does not create a local user, so a missing email claim is not a
reason to reject the token. Signature, expiry, and algorithm are checked
the same way as ``get_current_user``.
"""

import logging

from fastapi import HTTPException, status
from jose import JWTError, jwt

from ...core.auth_config import AuthSettings, get_auth_settings
from .jwks import get_clerk_jwks

logger = logging.getLogger(__name__)

_MAX_TOKEN_LENGTH = 8192


async def decode_verified_clerk_jwt(
    token: str,
    settings: AuthSettings | None = None,
) -> dict:
    """Return verified Clerk claims, or raise 401/503.

    Failure details are generic. Jose's own messages can quote token
    segments, and those must not reach the client or the logs.
    """
    if not token or len(token) > _MAX_TOKEN_LENGTH or token.count(".") != 2:
        raise _unauthorized()

    auth = settings or get_auth_settings()
    try:
        jwks = await get_clerk_jwks(auth)
        signing_key = _signing_key(jwks, token)
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise _unauthorized() from None
        raise
    except JWTError:
        logger.error("Clerk session token failed verification")
        raise _unauthorized() from None


def _signing_key(jwks: dict, token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        logger.error("Clerk session token header could not be read")
        raise _unauthorized() from None

    kid = header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    logger.error("Clerk session token signing key was not found")
    raise _unauthorized()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
