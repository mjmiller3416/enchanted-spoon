# Founder promo and the $0 trial invoice (test clock)

**Monthly FOUNDER30: verified by the lead.** A 7-day trial checkout with FOUNDER30 succeeded. The first paid invoice was **$4.89** (30% off $6.99). The $0 trial invoice did not block `restrictions.first_time_transaction`.

**Annual FOUNDER30Y: failed, replacement pending.** Stripe rejected it with `promotion_code_amount_insufficient`. The code had a $49.99 `minimum_amount`, and Stripe checked that minimum against the **$0 trial invoice**, not the later $49.99 annual charge. The lead is replacing it with a promotion code that has **no minimum**. Put that new id in `STRIPE_PROMO_FOUNDER30_ANNUAL`. Do not reuse the old id.

This server does not read `restrictions.minimum_amount` and does not send one. Nothing in checkout depends on that Stripe restriction.

## What we send

For a customer with no invoices and `has_used_trial=false`:

- `mode=subscription`
- `line_items` with `STRIPE_PRICE_PRO_MONTHLY_V2` or `STRIPE_PRICE_PRO_ANNUAL_V2` (monthly falls back to `STRIPE_PRICE_ID_PRO`)
- `subscription_data.trial_period_days=7`
- `subscription_data.trial_settings.end_behavior.missing_payment_method=cancel`
- `discounts=[{promotion_code}]` using `STRIPE_PROMO_FOUNDER30_MONTHLY` or `STRIPE_PROMO_FOUNDER30_ANNUAL` when set. When those variables are unset, FOUNDER30 and FOUNDER30Y stay live: Checkout looks the typed code up in Stripe (`PromotionCode.list(code=...)`). Only `FOUNDER_OFFER_ENDS_AT`, or deactivating the codes in Stripe, turns that lookup off. Unset promo env vars do not disable the offer.
- no `allow_promotion_codes`
- no `payment_method_collection=if_required` (card stays required)
- no `minimum_amount`
- `automatic_tax.enabled=true`

FOUNDER30 is accepted only with the monthly price. FOUNDER30Y is accepted only with the annual price. That plan lock is `offer["plan"] != plan` in `backend/app/services/founder_codes.py` (`lookup_founder_promotion`). Customers who already used a trial are rejected in `BillingService.create_checkout_session` before the promo id is attached. The offer also ends at `FOUNDER_OFFER_ENDS_AT` (default Mar 31, 2027, 11:59 PM ET).

The coupons to mirror in **test mode** are:

- FOUNDER30: 30% off, repeating, 3 months, first-time customers, cap 70. No minimum amount.
- FOUNDER30Y replacement: $10 off once, first-time customers, cap 30. **No `minimum_amount`.**

This account's API version creates promotion codes with `promotion[type]=coupon&promotion[coupon]=` rather than a top-level `coupon` parameter. The lookup still accepts either shape.

The 3 discounted months are supposed to start on the first paid invoice after the trial. The monthly test-clock run produced the discounted first paid invoice ($4.89). It did not by itself prove when the repeating coupon clock started. Advance through 3 paid months before relying on month 4 being full price.

## Test-clock procedure (test mode only)

1. In a Stripe **test** account, create the two coupons and promotion codes above. Do not use the live promotion-code ids. The annual code must omit `minimum_amount`.
2. Create a test clock and a customer on that clock.
3. Run local Checkout against `sk_test_...` with code `FOUNDER30` and the monthly test price.
4. If Checkout rejects the code with a first-time-customer error before any invoice exists, stop and report that. Our server does not pre-reject Stripe's `first_time_transaction` flag; it does reject `has_used_trial`.
5. Open the subscription. The first invoice should be $0 (trial).
6. Advance the clock 7 days so the first paid invoice is created.
7. Record whether that invoice has the 30% discount. The lead's run did: **$4.89**.
8. If it does not, record the Stripe error. The monthly run did not treat the $0 trial invoice as blocking `first_time_transaction`.
9. Advance through 3 paid months and confirm the 4th paid invoice is full price. If the discount expired earlier, the coupon clock started at subscription creation (during the trial) rather than at the first paid invoice.
10. Repeat steps 3–7 with `FOUNDER30Y` and the annual price, using the replacement promo id (no minimum). The old code failed here with `promotion_code_amount_insufficient`. The first paid invoice (after 7 days, for the year) should be $10 off $49.99.

A customer that already has any invoice, including a $0 one, is not reused. The next Checkout creates a new Stripe customer so the first-time restriction is evaluated on a customer with an empty invoice history.
