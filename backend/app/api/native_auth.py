"""Trade a native Clerk session for a short-lived browser sign-in token.

The Android and iOS shells finish Google and Apple OAuth on a native
Frontend API client (separate cookie jar from the WebView). This route
checks that client's session JWT, asks Clerk for a sign-in token that
expires in about a minute, and returns only that token. The WebView then
calls ``signIn.create({ strategy: "ticket" })``.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.auth.session_jwt import decode_verified_clerk_jwt
from app.core.rate_limit import ip_limiter, limiter
from app.dtos.native_auth import NativeTicketResponseDTO
from app.services.clerk_service import ClerkApiError, issue_browser_sign_in_ticket

logger = logging.getLogger(__name__)

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

_USER_ID = re.compile(r"^user_[A-Za-z0-9]+$")
_SESSION_ID = re.compile(r"^sess_[A-Za-z0-9]+$")

_UNAVAILABLE = "Sign-in could not be completed. Please try again."


def _session_owner(payload: dict) -> tuple[str, str]:
    sub = payload.get("sub")
    sid = payload.get("sid")
    if not isinstance(sub, str) or not _USER_ID.match(sub):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not isinstance(sid, str) or not _SESSION_ID.match(sid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return sub, sid


@router.post("/native-ticket", response_model=NativeTicketResponseDTO)
@limiter.limit("10/minute")
@ip_limiter.limit("30/minute")
async def create_native_ticket(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> NativeTicketResponseDTO:
    """Verify a native session JWT and return a one-minute sign-in ticket.

    ``AUTH_DISABLED`` does not apply. A missing or unverified token is 401.
    The native session is revoked after the ticket is issued when Clerk
    accepts the revoke; the ticket is still returned if revoke fails.
    """
    if credentials is None or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = await decode_verified_clerk_jwt(credentials.credentials.strip())
    user_id, session_id = _session_owner(payload)

    try:
        ticket = issue_browser_sign_in_ticket(user_id, session_id)
    except ClerkApiError as exc:
        logger.error("Native sign-in ticket was not issued: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_UNAVAILABLE,
        ) from None

    return NativeTicketResponseDTO(ticket=ticket)
