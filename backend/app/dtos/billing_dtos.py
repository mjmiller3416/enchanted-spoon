"""app/dtos/billing_dtos.py

DTOs for Stripe billing endpoints (Checkout session, billing portal).
"""

from __future__ import annotations

from pydantic import BaseModel


class CheckoutSessionResponseDTO(BaseModel):
    """Response DTO for POST /api/billing/checkout-session."""

    checkout_url: str


class PortalSessionResponseDTO(BaseModel):
    """Response DTO for POST /api/billing/portal-session."""

    portal_url: str


__all__ = [
    "CheckoutSessionResponseDTO",
    "PortalSessionResponseDTO",
]
