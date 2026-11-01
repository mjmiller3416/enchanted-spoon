"""app/dtos/billing_dtos.py

DTOs for Stripe billing endpoints (Checkout session, billing portal)
and the native store entitlement sync.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CheckoutSessionRequestDTO(BaseModel):
    """Body for POST /api/billing/checkout-session."""

    interval: Literal["month", "year"] = "month"


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
    "PortalSessionResponseDTO",
    "StoreSyncResponseDTO",
]
