# Post-deploy checklist

Do these by hand after this branch is deployed. This change does not create Stripe prices, archive prices, or edit Railway variables.

- Archive the old $4.99 Pro price in Stripe. Leave it archived so existing subscriptions can keep renewing on it until they move, and point new Checkout only at `STRIPE_PRICE_PRO_MONTHLY_V2` ($6.99/mo) and `STRIPE_PRICE_PRO_ANNUAL_V2` ($49.99/yr).
- Confirm Stripe Tax is enabled on the account. Checkout sends `automatic_tax.enabled=true` and the prices are tax-exclusive.
- Confirm `STRIPE_CHECKOUT_ENABLED=true` only when live checkout should open. It stays false until that switch is flipped.
- If Railway still sets `GEMINI_MODEL`, `GEMINI_ASSISTANT_MODEL`, or `GEMINI_IMAGE_MODEL`, those values override the new code defaults (`gemini-3.6-flash` for the assistant, `gemini-3.1-flash-lite` / `gemini-3.5-flash-lite` for the other text features, `gemini-3.1-flash-lite-image` for photos).
- Set `LEGACY_FREE_CUTOFF` to the coordinated release deploy time (ISO 8601). Accounts created before that instant keep free until Mar 31, 2027, 11:59 PM ET. Leave it unset and nobody is grandfathered. PR #209 currently hardcodes 2026-10-31; it should read this same variable.
- Schedule `python -m app.scripts.free_tier_sunset` daily. It no-ops the migration until Mar 31, 2027, 11:59 PM ET, and emits the 30/7/1-day reminder hooks.
- The per-IP limiter uses the rightmost `X-Forwarded-For` hop, which Railway's proxy appends. The leftmost value is client-supplied and is not trusted. uvicorn is not started with `--proxy-headers`.
- Run the test-clock procedure in `docs/stripe-test-clock-founder-promo.md` in Stripe test mode before relying on FOUNDER30.

# Manual verification (no live keys)

Use a Stripe **test-mode** sandbox and a local backend. Do not point this at production or `sk_live_` keys.

1. Set `STRIPE_SECRET_KEY=sk_test_...`, the test-mode price ids, `STRIPE_CHECKOUT_ENABLED=true`, and `AUTH_DISABLED=true`.
2. Start the API and open Settings → Plan & Billing. Choose monthly or annual, optionally enter FOUNDER30 / FOUNDER30Y, and complete Checkout with card `4242`.
3. Confirm the Checkout page shows tax as extra ("plus applicable tax") and collects a card.
4. In the Stripe dashboard test clock, advance 7 days and confirm the first paid invoice is discounted and the trial invoice was $0.
5. Generate a photo from a recipe. Confirm one square image, a cropped banner, and the usage meter moving by one.
6. Hit an AI cap and confirm the meter and the 429.
