"""app/api/billing.py

FastAPI router for Stripe billing endpoints: Checkout session creation
and billing-portal link generation.

Note: the Stripe webhook handler (which writes subscription state back
onto the User) is tracked separately and is not part of this router.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.db import get_session
from app.dtos.billing_dtos import CheckoutSessionResponseDTO, PortalSessionResponseDTO
from app.models.user import User
from app.services.billing_service import (
    BillingService,
    CheckoutSessionError,
    PortalSessionError,
    StripeCustomerError,
    StripeNotConfiguredError,
)

router = APIRouter()


@router.post("/checkout-session", response_model=CheckoutSessionResponseDTO)
def create_checkout_session(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a Stripe Checkout session for the Pro subscription.

    Creates the user's Stripe customer on first use. Returns the
    redirect URL the frontend should send the user to.
    """
    service = BillingService(session)
    try:
        checkout_url = service.create_checkout_session(current_user)
    except StripeNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except (StripeCustomerError, CheckoutSessionError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return CheckoutSessionResponseDTO(checkout_url=checkout_url)


@router.post("/portal-session", response_model=PortalSessionResponseDTO)
def create_portal_session(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Create a Stripe billing-portal session for the current user.

    Returns a URL where the user can manage or cancel their subscription.
    """
    service = BillingService(session)
    try:
        portal_url = service.create_portal_session(current_user)
    except StripeNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except PortalSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PortalSessionResponseDTO(portal_url=portal_url)
