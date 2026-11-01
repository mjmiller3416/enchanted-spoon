"""app/dtos/billing_dtos.py

DTOs for Stripe billing endpoints (Checkout session, billing portal)
and the native store entitlement sync.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CheckoutSessionRequestDTO(BaseModel):
    """POST /api/billing/checkout-session. Empty body starts monthly checkout."""

    plan: str = Field(default="monthly", pattern="^(monthly|annual)$")
    promotion_code: str | None = None


class FounderSpotDTO(BaseModel):
    code: str
    plan: str
    spots_remaining: int | None = None
    spots_total: int | None = None


class FounderOfferResponseDTO(BaseModel):
    ends_at: datetime
    monthly: FounderSpotDTO
    annual: FounderSpotDTO


class CheckoutSessionResponseDTO(BaseModel):
    """Response DTO for POST /api/billing/checkout-session."""

    checkout_url: str


class PortalSessionResponseDTO(BaseModel):
    """Response DTO for POST /api/billing/portal-session."""

    portal_url: str


class StoreSyncResponseDTO(BaseModel):
    """Response DTO for POST /api/billing/store/sync."""

    result: str = Field(description="applied, ignored, or trial_suppressed")


__all__ = [
    "CheckoutSessionRequestDTO",
    "CheckoutSessionResponseDTO",
    "FounderOfferResponseDTO",
    "FounderSpotDTO",
    "PortalSessionResponseDTO",
    "StoreSyncResponseDTO",
]
