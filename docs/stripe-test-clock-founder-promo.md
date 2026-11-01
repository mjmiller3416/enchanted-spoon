# Founder promo and the $0 trial invoice (test clock)

**Status: unverified.** This environment has no Stripe test-mode keys, and production keys must not be used. The automated test `test_checkout_attaches_trial_tax_and_first_time_promo_before_any_invoice` only checks the Checkout payload we send. It does not prove how Stripe evaluates `restrictions.first_time_transaction`.

## What we send

For a customer with no invoices and `has_used_trial=false`:

- `mode=subscription`
- `line_items` with `STRIPE_PRICE_PRO_MONTHLY_V2` or `STRIPE_PRICE_PRO_ANNUAL_V2` (monthly falls back to `STRIPE_PRICE_ID_PRO`)
- `subscription_data.trial_period_days=7`
- `subscription_data.trial_settings.end_behavior.missing_payment_method=cancel`
- `discounts=[{promotion_code}]` after a server lookup of the typed code
- no `allow_promotion_codes`
- no `payment_method_collection=if_required` (card stays required)
- `automatic_tax.enabled=true`

FOUNDER30 is accepted only with the monthly price. FOUNDER30Y is accepted only with the annual price. The coupons to mirror in **test mode** are:

- FOUNDER30: 30% off, repeating, 3 months, first-time customers, cap 70
- FOUNDER30Y: $10 off once, first-time customers, cap 30, minimum $49.99

The 3 discounted months are supposed to start on the first paid invoice after the trial. Stripe starts a repeating coupon when it is attached. That timing has to be confirmed with a test clock, not assumed.

## Test-clock procedure (test mode only)

1. In a Stripe **test** account, create the two coupons and promotion codes above. Do not use the live promotion-code ids.
2. Create a test clock and a customer on that clock.
3. Run local Checkout against `sk_test_...` with code `FOUNDER30` and the monthly test price.
4. If Checkout rejects the code with a first-time-customer error before any invoice exists, stop and report that. Our server does not pre-reject `first_time_transaction`.
5. Open the subscription. The first invoice should be $0 (trial).
6. Advance the clock 7 days so the first paid invoice is created.
7. Record whether that invoice has the 30% discount.
8. If it does not, record the Stripe error. In particular, note if the $0 trial invoice was counted as the customer's first transaction and the promotion was dropped.
9. Advance through 3 paid months and confirm the 4th paid invoice is full price. If the discount expired earlier, the coupon clock started at subscription creation (during the trial) rather than at the first paid invoice.
10. Repeat steps 3–7 with `FOUNDER30Y` and the annual price. The first paid invoice (after 7 days, for the year) should be $10 off.

A customer that already has any invoice, including a $0 one, is not reused. The next Checkout creates a new Stripe customer so the first-time restriction is evaluated on a customer with an empty invoice history.
