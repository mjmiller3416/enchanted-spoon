"""app/api/auth/api_key.py

Shared API-key authentication for trusted first-party app-to-app calls.

Integration endpoints (e.g. the Tada shopping-list ingest) are authenticated
with a static shared secret sent in the X-API-Key header, compared against the
INTEGRATION_API_KEY env var. The authenticated caller is an app, not a person,
so all writes land on the single user configured via INTEGRATION_USER_ID.
"""

import logging
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from ...core.auth_config import AuthSettings, get_auth_settings
from ...database.db import get_session
from ...models.user import User
from ...services.user_service import UserService

logger = logging.getLogger(__name__)

# auto_error=False so we can return a consistent 401 instead of FastAPI's default 403
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_integration_user(
    api_key: Optional[str] = Security(api_key_header),
    session: Session = Depends(get_session),
    settings: AuthSettings = Depends(get_auth_settings),
) -> User:
    """
    Dependency that authenticates a trusted first-party app via shared API key
    and resolves the user account its writes should be applied to.

    Usage:
        @router.post("/external/items")
        def upsert_external_item(target_user: User = Depends(get_integration_user)):
            ...

    Returns:
        User: The configured integration target user.

    Raises:
        HTTPException 401: Missing or invalid API key.
        HTTPException 503: Integration auth not configured on this deployment.
    """
    if not settings.integration_api_key or settings.integration_user_id is None:
        logger.warning("Integration endpoint called but INTEGRATION_API_KEY/INTEGRATION_USER_ID not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integration API is not configured on this server",
        )

    # Compare as bytes: compare_digest raises TypeError on non-ASCII str input
    if not api_key or not secrets.compare_digest(
        api_key.encode("utf-8"), settings.integration_api_key.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    user = UserService(session).get_by_id(settings.integration_user_id)
    if not user:
        logger.error(f"INTEGRATION_USER_ID={settings.integration_user_id} does not match any user")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integration target user is not configured correctly",
        )

    return user
