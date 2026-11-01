"""Server-side FOUNDER30 / FOUNDER30Y checks for web Checkout.

Promotion-code ids come from ``STRIPE_PROMO_FOUNDER30_MONTHLY`` and
``STRIPE_PROMO_FOUNDER30_ANNUAL`` when set, so a replacement id can be
changed in Railway without a code change. Otherwise Checkout looks the
typed code up in Stripe and then passes ``discounts=[{promotion_code}]``.
FOUNDER30 is monthly only. FOUNDER30Y is annual only.
``allow_promotion_codes`` is never enabled. ``restrictions.minimum_amount``
is never read and is not required.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import stripe

from ..core.offer_windows import founder_offer_ends_at

FOUNDER_OFFERS = {
    "FOUNDER30": {"plan": "monthly", "coupon_id": "FOUNDER30_MONTHLY"},
    "FOUNDER30Y": {"plan": "annual", "coupon_id": "FOUNDER30_ANNUAL"},
}

PROMO_ID_ENV = {
    "FOUNDER30": "STRIPE_PROMO_FOUNDER30_MONTHLY",
    "FOUNDER30Y": "STRIPE_PROMO_FOUNDER30_ANNUAL",
}


class PromotionCodeRejected(Exception):
    """The typed code cannot be attached to this checkout."""


def normalize_founder_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    code = raw.strip().upper()
    return code or None


def configured_promotion_id(code: str) -> str | None:
    """Railway promo id for this typed code, or None when the env var is unset."""
    env_name = PROMO_ID_ENV.get(code)
    if env_name is None:
        return None
    value = os.getenv(env_name, "").strip()
    return value or None


def _coupon_id(promo: dict) -> str | None:
    """Coupon id from either the legacy ``coupon`` field or ``promotion.coupon``.

    This account's API version creates codes with
    ``promotion[type]=coupon&promotion[coupon]=``.
    """
    coupon = promo.get("coupon")
    promotion = promo.get("promotion")
    if coupon is None and isinstance(promotion, dict) and promotion.get("type") == "coupon":
        coupon = promotion.get("coupon")
    if isinstance(coupon, str):
        return coupon
    if isinstance(coupon, dict):
        value = coupon.get("id")
        return value if isinstance(value, str) else None
    return None


def _as_dict(value: Any) -> dict:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return value
    data = getattr(value, "data", None)
    if data is not None and len(data) == 0:
        return {"data": []}
    return {}


def lookup_founder_promotion(code: str, plan: str, now: datetime | None = None) -> str:
    """Return the Stripe promotion_code id for a valid founder code.

    First-time customers are rejected in ``BillingService`` when
    ``has_used_trial`` is already set. ``restrictions.minimum_amount`` is
    not consulted. A configured promo id is returned as-is after the plan
    and end-date checks.
    """
    offer = FOUNDER_OFFERS.get(code)
    if offer is None:
        raise PromotionCodeRejected("That code isn't a founding offer.")
    # FOUNDER30 is monthly only. FOUNDER30Y is annual only.
    if offer["plan"] != plan:
        expected = "monthly" if offer["plan"] == "monthly" else "annual"
        raise PromotionCodeRejected(f"{code} only works with the {expected} plan.")

    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    if moment > founder_offer_ends_at():
        raise PromotionCodeRejected("The founding offer has ended.")

    configured = configured_promotion_id(code)
    if configured:
        return configured

    listed = stripe.PromotionCode.list(code=code, active=True, limit=1)
    payload = listed.to_dict() if hasattr(listed, "to_dict") else listed
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not rows:
        raise PromotionCodeRejected("That founding code is not active.")
    promo = _as_dict(rows[0])
    if promo.get("active") is False:
        raise PromotionCodeRejected("That founding code is not active.")
    expires = promo.get("expires_at")
    if isinstance(expires, int) and expires <= int(moment.timestamp()):
        raise PromotionCodeRejected("That founding code has expired.")
    maximum = promo.get("max_redemptions")
    redeemed = promo.get("times_redeemed") or 0
    if isinstance(maximum, int) and redeemed >= maximum:
        raise PromotionCodeRejected("That founding code is fully redeemed.")
    coupon_id = _coupon_id(promo)
    if coupon_id and coupon_id != offer["coupon_id"]:
        raise PromotionCodeRejected("That code doesn't match this plan.")
    promo_id = promo.get("id")
    if not isinstance(promo_id, str) or not promo_id:
        raise PromotionCodeRejected("That founding code could not be applied.")
    return promo_id


def founder_spots(code: str) -> dict:
    """Remaining redemptions, or None when Stripe can't be asked."""
    offer = FOUNDER_OFFERS[code]
    try:
        configured = configured_promotion_id(code)
        if configured:
            promo = _as_dict(stripe.PromotionCode.retrieve(configured))
            return _spots_from_promo(code, offer["plan"], promo)
        listed = stripe.PromotionCode.list(code=code, limit=1)
    except stripe.error.StripeError:
        return {"code": code, "plan": offer["plan"], "spots_remaining": None, "spots_total": None}
    payload = listed.to_dict() if hasattr(listed, "to_dict") else listed
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not rows:
        return {"code": code, "plan": offer["plan"], "spots_remaining": None, "spots_total": None}
    promo = _as_dict(rows[0])
    return _spots_from_promo(code, offer["plan"], promo)


def _spots_from_promo(code: str, plan: str, promo: dict) -> dict:
    total = promo.get("max_redemptions")
    redeemed = promo.get("times_redeemed") or 0
    remaining = None
    if isinstance(total, int):
        remaining = max(total - int(redeemed), 0)
    return {
        "code": code,
        "plan": plan,
        "spots_remaining": remaining,
        "spots_total": total if isinstance(total, int) else None,
    }
