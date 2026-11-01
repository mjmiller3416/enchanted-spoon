"""app/api/billing.py

FastAPI router for Stripe billing endpoints: Checkout session creation
and billing-portal link generation.

Note: the Stripe webhook handler (which writes subscription state back
onto the User) is tracked separately and is not part of this router.
"""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
import stripe

from app.api.auth import get_current_user
from app.core.offer_windows import founder_offer_ends_at
from app.core.stripe_config import get_stripe_settings
from app.database.db import get_session
from app.dtos.billing_dtos import (
    CheckoutSessionRequestDTO,
    CheckoutSessionResponseDTO,
    FounderOfferResponseDTO,
    PortalSessionResponseDTO,
)
from app.models.user import User
from app.services.billing_service import (
    BillingService,
    CheckoutSessionError,
    PortalSessionError,
    StripeCustomerError,
    StripeNotConfiguredError,
)
from app.services.founder_codes import PromotionCodeRejected, founder_spots

router = APIRouter()


@router.get("/founder-offer", response_model=FounderOfferResponseDTO)
def get_founder_offer() -> FounderOfferResponseDTO:
    """Remaining founding spots. Missing Stripe data hides the spots line."""

    settings = get_stripe_settings()
    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key
        monthly = founder_spots("FOUNDER30")
        annual = founder_spots("FOUNDER30Y")
    else:
        monthly = {"code": "FOUNDER30", "plan": "monthly", "spots_remaining": None, "spots_total": None}
        annual = {"code": "FOUNDER30Y", "plan": "annual", "spots_remaining": None, "spots_total": None}
    return FounderOfferResponseDTO(
        ends_at=founder_offer_ends_at(),
        monthly=monthly,
        annual=annual,
    )


@router.post("/checkout-session", response_model=CheckoutSessionResponseDTO)
def create_checkout_session(
    body: CheckoutSessionRequestDTO | None = Body(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for monthly or annual Pro."""
    payload = body or CheckoutSessionRequestDTO()
    service = BillingService(session)
    try:
        checkout_url = service.create_checkout_session(
            current_user,
            plan=payload.plan,
            promotion_code=payload.promotion_code,
        )
    except PromotionCodeRejected as e:
        raise HTTPException(status_code=400, detail=str(e))
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
