"""app/api/stripe_webhooks.py

FastAPI router for the Stripe webhook endpoint.
Public route (no Clerk auth) - trust is established via Stripe's signature
on the raw request body instead of a bearer token.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.stripe_config import StripeSettings, get_stripe_settings
from app.database.db import get_session
from app.services.stripe_webhook_service import (
    InvalidStripeSignatureError,
    StripeWebhookProcessingError,
    StripeWebhookService,
)

router = APIRouter()


@router.post("")
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    session: Session = Depends(get_session),
    settings: StripeSettings = Depends(get_stripe_settings),
):
    """
    Receive and process a Stripe webhook event.

    Verifies the `Stripe-Signature` header against the raw request body before
    trusting anything in the payload. Handles checkout completion, invoice
    payment, and subscription update/cancellation events to keep each user's
    `subscription_tier`/`subscription_status`/`subscription_ends_at` in sync.
    """
    payload = await request.body()
    service = StripeWebhookService(session)

    try:
        event = service.verify_and_parse_event(payload, stripe_signature, settings)
    except InvalidStripeSignatureError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        service.handle_event(event)
    except StripeWebhookProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"received": True}
