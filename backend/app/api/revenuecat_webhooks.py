"""app/api/revenuecat_webhooks.py

RevenueCat webhook for App Store and Play Billing entitlements.

Public route. Trust comes from the Authorization header configured in the
RevenueCat dashboard (``REVENUECAT_WEBHOOK_AUTHORIZATION``), not from a
Clerk token. Stripe events that RevenueCat may also forward are ignored
inside the entitlement service.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.native_billing_config import (
    NativeBillingSettings,
    authorization_matches,
    get_native_billing_settings,
)
from app.database.db import get_session
from app.services.entitlement_service import (
    EntitlementService,
    UnknownStoreUserError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def handle_revenuecat_webhook(
    request: Request,
    session: Session = Depends(get_session),
    settings: NativeBillingSettings = Depends(get_native_billing_settings),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """
    Apply a RevenueCat subscription event to the matching account.

    Returns 200 for events we intentionally skip so RevenueCat does not
    retry them. An unknown numeric app user id returns 500 so a purchase
    that races account creation is retried.
    """
    if not settings.webhook_configured:
        logger.error("RevenueCat webhook called but REVENUECAT_WEBHOOK_AUTHORIZATION is unset")
        raise HTTPException(status_code=503, detail="Store webhook is not configured")

    if not authorization_matches(authorization, settings.revenuecat_webhook_authorization):
        logger.warning("RevenueCat webhook authorization failed")
        raise HTTPException(status_code=401, detail="Invalid webhook authorization")

    if not settings.native_iap_enabled:
        # Ack so RevenueCat stops retrying, and drop the event. Turn the
        # flag on before pointing the dashboard at this URL.
        logger.info("Ignoring RevenueCat webhook because NATIVE_IAP_ENABLED is false")
        return {"received": True, "result": "disabled"}

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event = payload.get("event") if isinstance(payload, dict) else None
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="Missing event")

    service = EntitlementService(session, settings)
    try:
        result = service.apply_revenuecat_event(event)
    except UnknownStoreUserError:
        logger.warning("RevenueCat event referenced an unknown app_user_id")
        raise HTTPException(status_code=500, detail="Unknown app user")

    return {"received": True, "result": result}
