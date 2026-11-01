# Post-deploy checklist

Set the cutoff before the deploy. The rest of this list is after the branch is deployed. This change does not create Stripe prices, archive prices, or edit Railway variables itself.

- **Before deploy:** set the Railway variable `LEGACY_FREE_CUTOFF` on the backend to the coordinated release timestamp (ISO 8601). Naive values are Eastern. Accounts created before that instant keep free AI until Mar 31, 2027, 11:59 PM ET. If it is left unset, startup logs a critical error, `/health` and `GET /api/admin/status` report `legacy_free_cutoff_configured: false`, and every account is treated as legacy so existing free users are not dropped to the no-AI tier. PR #209 should read this same variable instead of its hardcoded 2026-10-31.
- Archive the old $4.99 Pro price in Stripe. Leave it archived so existing subscriptions can keep renewing on it until they move, and point new Checkout only at `STRIPE_PRICE_PRO_MONTHLY_V2` ($6.99/mo) and `STRIPE_PRICE_PRO_ANNUAL_V2` ($49.99/yr).
- Confirm Stripe Tax is enabled on the account. Checkout sends `automatic_tax.enabled=true` and the prices are tax-exclusive.
- Confirm `STRIPE_CHECKOUT_ENABLED=true` only when live checkout should open. It stays false until that switch is flipped.
- If Railway still sets `GEMINI_MODEL`, `GEMINI_ASSISTANT_MODEL`, or `GEMINI_IMAGE_MODEL`, those values override the new code defaults (`gemini-3.6-flash` for the assistant, `gemini-3.1-flash-lite` / `gemini-3.5-flash-lite` for the other text features, `gemini-3.1-flash-lite-image` for photos).
- Legacy Pro subscribers and granted testers move to the launch Pro caps at deploy: 20 photos, 300 chats, 200 suggestions, 50 imports per month. Before release, set the Railway variable `ADMIN_EXEMPT_EMAILS` on the backend to the two accounts that must stay uncapped. It is comma-separated, case-insensitive, and trimmed. A match uses only Clerk's verified primary email. Those accounts get uncapped AI and read-only admin views. They cannot call admin mutations such as `PATCH /api/admin/users/{id}/usage-exempt`. Mutations require `users.is_admin` or `USAGE_EXEMPT_USER_IDS`. Do not put the addresses in the repo. `usage_exempt` in Admin → Users and `USAGE_EXEMPT_USER_IDS` still keep the previous Pro allowances (150 photos, 500 chats, 300 suggestions, 100 imports). The id list can also call admin mutations. A trial, expired, free, or new account is not moved onto those old allowances by `usage_exempt` alone.
- Web and the #209 native paywall must open trial checkout when the JSON error code is `trial_required` (`detail.error`). Do not key that route off HTTP 403. The same status is also used for read-only accounts and for "Pro subscription required".
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
