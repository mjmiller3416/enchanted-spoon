"""Cron entry point that delivers due trial nudges.

Protected by ``PUSH_DISPATCH_SECRET``. With the secret unset the route
refuses the call so it cannot be used as an open relay.
"""

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database.db import get_session
from app.services.push_service import PushService

router = APIRouter()


@router.post("/dispatch")
def dispatch_trial_nudges(
    session: Session = Depends(get_session),
    dispatch_key: str | None = Header(default=None, alias="X-Push-Dispatch-Key"),
):
    expected = os.environ.get("PUSH_DISPATCH_SECRET")
    if not expected:
        raise HTTPException(status_code=503, detail="Push dispatch is not configured.")
    if not dispatch_key or not secrets.compare_digest(dispatch_key, expected):
        raise HTTPException(status_code=401, detail="Invalid dispatch key.")
    return PushService(session).dispatch_due()
