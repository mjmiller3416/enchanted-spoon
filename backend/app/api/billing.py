"""app/api/billing.py

FastAPI router for billing: Stripe Checkout, the billing portal, and the
authenticated store-entitlement sync used after a native purchase.

The Stripe webhook and the RevenueCat webhook write subscription state.
They live on their own routers.
"""

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from sqlalchemy.orm import Session
import stripe

from app.api.auth import get_current_user
from app.core.native_billing_config import is_native_billing_client
from app.core.offer_windows import founder_offer_ends_at
from app.core.stripe_config import get_stripe_settings
from app.database.db import get_session
from app.dtos.billing_dtos import (
    CheckoutSessionRequestDTO,
    CheckoutSessionResponseDTO,
    FounderOfferResponseDTO,
    PortalSessionResponseDTO,
    StoreSyncResponseDTO,
)
from app.models.user import User
from app.services.billing_service import (
    BillingService,
    CheckoutSessionError,
    PortalSessionError,
    StripeCustomerError,
    StripeNotConfiguredError,
)
from app.services.entitlement_service import (
    EntitlementService,
    NativeIapDisabledError,
    NativeIapNotConfiguredError,
    RevenueCatApiError,
)
from app.services.founder_codes import PromotionCodeRejected, founder_spots

router = APIRouter()

_NATIVE_BILLING_DETAIL = (
    "Subscriptions in the app are purchased through the App Store or Google Play."
)


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
    client: str | None = Header(default=None, alias="X-Enchanted-Spoon-Client"),
):
    """Create a Stripe Checkout session for monthly or annual Pro.

    Refused when the request comes from the native shell. Digital
    subscriptions inside the iOS and Android apps use in-app purchase.
    """
    if is_native_billing_client(client):
        raise HTTPException(status_code=403, detail=_NATIVE_BILLING_DETAIL)

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
    client: str | None = Header(default=None, alias="X-Enchanted-Spoon-Client"),
):
    """
    Create a Stripe billing-portal session for the current user.

    Returns a URL where the user can manage or cancel their subscription.
    Refused from the native shell so the app does not link to an external
    payment flow.
    """
    if is_native_billing_client(client):
        raise HTTPException(status_code=403, detail=_NATIVE_BILLING_DETAIL)

    service = BillingService(session)
    try:
        portal_url = service.create_portal_session(current_user)
    except StripeNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except PortalSessionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PortalSessionResponseDTO(portal_url=portal_url)


@router.post("/store/sync", response_model=StoreSyncResponseDTO)
def sync_store_entitlement(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Pull the signed-in account's store entitlement from RevenueCat.

    The client calls this after a purchase or a restore. The webhook is
    the durable path; this call lets the account update without waiting
    for it. The client cannot grant itself Pro — the server reads
    RevenueCat with the secret key.
    """
    service = EntitlementService(session)
    try:
        result = service.sync_from_revenuecat(current_user)
    except NativeIapDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except NativeIapNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RevenueCatApiError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return StoreSyncResponseDTO(result=result)
