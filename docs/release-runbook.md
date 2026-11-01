# Release runbook

Coordinated launch of #206, #210, #207, #208, and #209. Do not squash. A squash of an earlier PR produces a new commit the later branches do not contain, and the clean merge order below depends on merge commits.

Nothing in this document flips production flags or merges to `main`.

## Merge order and method

Merge into `main` with a merge commit, in this order. On GitHub that is **Create a merge commit**, not squash and not rebase.

| Order | PR | Branch | Base when opened | What it adds |
| --- | --- | --- | --- | --- |
| 1 | #206 | `fix/soft-launch-readiness` | `main` | Usage plan, billing events, checkout guards |
| 2 | #210 | `cursor/ai-cost-trial-billing-0118` | `fix/soft-launch-readiness` | Trial, sunset, founder codes, usage hook |
| 3 | #207 | `cursor/social-recipe-import-8604` | `main` | TikTok and Instagram import, caption paste |
| 4 | #208 | `cursor/household-sharing-8604` | `main` | Households. Contains merge commits of #206, #210, and #207 |
| 5 | #209 | `cursor/capacitor-native-apps-6ed5` | `main` | iOS/Android shell. Contains merge commits of the four above, plus migration `b8e4c1a7d2f9` |

After #206 is on `main`, retarget #210 from `fix/soft-launch-readiness` to `main`, then merge it. #207, #208, and #209 already target `main`.

A local simulation of that sequence on current `main` (`d57536e`) merges with no conflicts. Conflicts that showed up before that, and how they were fixed:

- **#208** conflicted with #206+#210+#207 in auth dependencies, users, admin DTOs, the model package, the router, billing settings, and the usage type. Fixed by merge commits of those branches into `cursor/household-sharing-8604`. Households of two or more reserve AI usage on the owner through `set_household_usage_hooks`. The owner's Pro cap is multiplied by 1.5. Trial, read-only, and sunset behavior from #210 stay.
- **#209** conflicted with that stack in billing, Stripe webhooks, the user model, env example, paywall, settings billing, pricing, and the app shell. Fixed by a merge commit of the updated household branch into `cursor/capacitor-native-apps-6ed5`. Store paywall and push stay beside web checkout.
- #208 joins billing `e7b1c4a9d2f6` and household `f6b2c8d4e1a7` in empty revision `c4a8e2b1d7f3`, so that PR has one Alembic head.
- #209 joins that revision with native push `a7c2e9b4d1f0` (via `b8e4c1a7d2f9` and `d5b9f3c2e8a4`). `alembic upgrade head` is one target on #208 alone and again after #209.

## Environment variables

Collected from `backend/.env.example`, `frontend/.env.example`, and `docs/post-deploy-checklist.md`. "Owner supplies" means the value is a secret or an id that is not in the repo.

`LEGACY_FREE_CUTOFF` is a **required pre-deploy** step on the backend service. Set it before the new process starts. If `ENVIRONMENT` or `RAILWAY_ENVIRONMENT` is `production` and the value is missing or not valid ISO 8601, startup refuses and Railway keeps the previous deploy. Naive timestamps are Eastern Time. Dev and test do not refuse: an unset value keeps every account on the legacy free plan.

`STRIPE_CHECKOUT_ENABLED` stays `false` on the backend until the smoke list below passes. Only then set it to `true`.

### Backend (Railway backend service)

| Name | Value | Required |
| --- | --- | --- |
| `LEGACY_FREE_CUTOFF` | Owner supplies. ISO 8601 release instant | Required, pre-deploy |
| `ENVIRONMENT` | `production` | Required |
| `ADMIN_EXEMPT_EMAILS` | Owner supplies. Comma-separated verified primary emails. Uncaps AI only | Required before release |
| `USAGE_EXEMPT_USER_IDS` | Owner supplies. Comma-separated user ids. Pre-release Pro allowances, and admin mutations | Optional |
| `SQLALCHEMY_DATABASE_URL` | Owner supplies. Production Postgres URL | Required |
| `CLERK_SECRET_KEY` | Owner supplies | Required |
| `CLERK_PUBLISHABLE_KEY` | Owner supplies | Required |
| `AUTH_DISABLED` | `false` | Required |
| `DEV_USER_ID` | `1` | Optional, local only |
| `INTEGRATION_API_KEY` | Owner supplies. Must match Hearth `ENCHANTED_SPOON_DEVICE_TOKEN` | Required if Hearth or Tada is on |
| `INTEGRATION_USER_ID` | Owner supplies | Required if those integrations are on |
| `CORS_ORIGINS` | `https://enchantedspoon.app` | Required |
| `STRIPE_SECRET_KEY` | Owner supplies. `sk_test_` until smoke, then live | Required |
| `STRIPE_WEBHOOK_SECRET` | Owner supplies (`whsec_`) | Required |
| `STRIPE_PRICE_ID_PRO` | Owner supplies. Previous Pro price. Used only if the monthly v2 price is unset | Optional |
| `STRIPE_PRICE_PRO_MONTHLY_V2` | Owner supplies. Existing $6.99/mo price id. Do not create a new price | Required for new checkout |
| `STRIPE_PRICE_PRO_ANNUAL_V2` | Owner supplies. Existing $49.99/yr price id | Required for annual checkout |
| `STRIPE_PROMO_FOUNDER30_MONTHLY` | Owner supplies (`promo_`). Monthly only | Optional. If unset, Checkout looks up `FOUNDER30` in Stripe |
| `STRIPE_PROMO_FOUNDER30_ANNUAL` | Owner supplies (`promo_`). Annual only, no `minimum_amount` | Optional. If unset, Checkout looks up `FOUNDER30Y` |
| `STRIPE_CHECKOUT_ENABLED` | `false` until smoke passes | Required |
| `FRONTEND_URL` | `https://enchantedspoon.app` | Required |
| `FREE_TIER_SUNSET_AT` | `2027-03-31T23:59:00` | Optional. Example default |
| `FOUNDER_OFFER_ENDS_AT` | `2027-03-31T23:59:00` | Optional. Turns founder-code lookup off after this instant |
| `GEMINI_ASSISTANT_API_KEY` | Owner supplies | Required |
| `GEMINI_TIP_API_KEY` | Owner supplies | Required |
| `GEMINI_IMAGE_API_KEY` | Owner supplies | Required |
| `GEMINI_RECIPE_GENERATION_API_KEY` | Owner supplies | Required |
| `GEMINI_NUTRITION_API_KEY` | Owner supplies | Required |
| `GEMINI_MODEL` | Leave unset. Overrides text-feature defaults | Optional |
| `GEMINI_ASSISTANT_MODEL` | Leave unset. Default `gemini-3.6-flash` | Optional |
| `GEMINI_IMAGE_MODEL` | Leave unset. Default `gemini-3.1-flash-lite-image` | Optional |
| `INSTAGRAM_OEMBED_ACCESS_TOKEN` | Owner supplies | Optional. Import uses the public page without it |
| `CLOUDINARY_CLOUD_NAME` | Owner supplies | Required |
| `CLOUDINARY_API_KEY` | Owner supplies | Required |
| `CLOUDINARY_API_SECRET` | Owner supplies | Required |
| `GITHUB_TOKEN` | Owner supplies | Optional |
| `GITHUB_REPO` | Owner supplies | Optional |
| `SENTRY_DSN` | Owner supplies | Optional |
| `SENTRY_TRACES_SAMPLE_RATE` | `0` | Optional |
| `APNS_KEY_ID` | Owner supplies | Optional until push |
| `APNS_TEAM_ID` | Owner supplies | Optional until push |
| `APNS_AUTH_KEY` | Owner supplies | Optional until push |
| `APNS_BUNDLE_ID` | `com.enchantedspoon.app` | Optional until push |
| `APNS_USE_SANDBOX` | `true` until production push | Optional |
| `FCM_SERVER_KEY` | Owner supplies | Optional until push |
| `PUSH_DISPATCH_SECRET` | Owner supplies | Optional until push |
| `NATIVE_IAP_ENABLED` | `false` until store products exist | Required |
| `REVENUECAT_WEBHOOK_AUTHORIZATION` | Owner supplies | Optional until IAP |
| `REVENUECAT_SECRET_API_KEY` | Owner supplies | Optional until IAP |
| `IAP_MONTHLY_PRODUCT_ID` | `com.enchantedspoon.app.pro.monthly` | Optional |
| `IAP_ANNUAL_PRODUCT_ID` | `com.enchantedspoon.app.pro.annual` | Optional |

### Frontend (Railway frontend service)

`NEXT_PUBLIC_*` values are baked into the web bundle the Capacitor shell loads. Change them only with a new frontend deploy.

| Name | Value | Required |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Production API origin | Required |
| `NEXT_PUBLIC_APP_URL` | `https://enchantedspoon.app` | Required |
| `NEXT_PUBLIC_NATIVE_IAP_ENABLED` | `false` | Required |
| `NEXT_PUBLIC_REVENUECAT_IOS_API_KEY` | Owner supplies | Optional until IAP |
| `NEXT_PUBLIC_REVENUECAT_ANDROID_API_KEY` | Owner supplies | Optional until IAP |
| `NEXT_PUBLIC_IAP_MONTHLY_PRODUCT_ID` | `com.enchantedspoon.app.pro.monthly` | Optional |
| `NEXT_PUBLIC_IAP_ANNUAL_PRODUCT_ID` | `com.enchantedspoon.app.pro.annual` | Optional |
| `NEXT_PUBLIC_FOUNDER_OFFER_ENDS_AT` | `2027-03-31T23:59:00` | Optional |
| `NEXT_PUBLIC_FOUNDER_OFFER_TIMEZONE` | `America/New_York` | Optional |
| `CAPACITOR_SERVER_URL` | Owner supplies. Used by `npx cap sync`, not the web bundle | Optional |

## Smoke tests

Run these with Stripe **test mode** (`sk_test_`) and `STRIPE_CHECKOUT_ENABLED=false` still set, except the checkout steps, which use a temporary `true` on a non-production backend or after you accept that test checkout is open. Do not use `sk_live_`. Card `4242` is enough.

1. **Health.** `GET /health` returns `status: healthy`. `legacy_free_cutoff_configured` is true and `legacy_free_cutoff_error` is absent.
2. **Sign-in.** A real Clerk user reaches the app. `AUTH_DISABLED` is false.
3. **Legacy free user AI.** An account created before `LEGACY_FREE_CUTOFF` can use AI and is metered on the free caps, not `trial_required`.
4. **New account.** An account created at or after the cutoff gets `detail.error == trial_required` on the first AI call. Do not key this off HTTP 403. The same status is also read-only and "Pro subscription required".
5. **Trial checkout.** With checkout enabled in test mode, start the 7-day trial. Stripe collects a card. The trial invoice is $0.
6. **FOUNDER30 monthly.** The code applies only to the monthly price. The first paid invoice after the trial is discounted.
7. **FOUNDER30Y annual-only.** The code applies only to the annual price. The promotion has no `minimum_amount`. Confirm with the test clock in `docs/stripe-test-clock-founder-promo.md`.
8. **Household.** Invite a second member. Both draw the owner's meter. With the owner on Pro, caps are the Pro numbers times 1.5. A household of one keeps that person's own tier.
9. **Social import.** Import a public TikTok or Instagram post. When the caption cannot be read, paste the caption and the import still produces a recipe.
10. **Admin exemption.** An email in `ADMIN_EXEMPT_EMAILS` is uncapped for AI and cannot open admin routes. An id in `USAGE_EXEMPT_USER_IDS` keeps the pre-release Pro allowances.
11. **Image one-call.** Generate a photo once. One square image is stored, the banner is cropped from it, and the usage meter moves by one.

After that list passes, set `STRIPE_CHECKOUT_ENABLED=true` for the live switch. Leave `NATIVE_IAP_ENABLED` and `NEXT_PUBLIC_NATIVE_IAP_ENABLED` false until store products exist.

## Rollback

Prefer this order. Schema and code move together.

1. **Railway.** Redeploy the previous successful deployment of the backend and the frontend. That restores the last good image without a new git commit. Do this first if the new process is crash-looping.
2. **Git.** If the bad commits are on `main`, revert the merge commits in reverse order: #209, then #208, then #207, then #210, then #206. `git revert -m 1 <merge-commit>` and push those revert commits. Do not reset `main`.
3. **Migrations.** After the code is back, downgrade the database. `d5b9f3c2e8a4` and `c4a8e2b1d7f3` and `b8e4c1a7d2f9` are empty merge revisions. `alembic downgrade -1` from `d5b9f3c2e8a4` only unlinks the latest pair. Repeat until the empty merges are gone, then downgrade each branch:
   - Billing, newest first: `e7b1c4a9d2f6` (usage exempt) → `d9f3b2c8e1a7` (pending trial checkout) → `c8e2a1b7d4f6` (trial and sunset columns) → `a6c1e4f9d3b5` drops `billing_events` → `f5b0d3e8c2a4` drops `users.usage_plan`. Dropping `usage_plan` forgets who was on the legacy allowance cohort.
   - Household `f6b2c8d4e1a7` drops `household_recipe_shares`, `household_invites`, `household_members`, then `households`. Do this while `users` still exists. Recipe rows stay; only the share links go away.
   - Native `a7c2e9b4d1f0` drops push tokens and trial nudges, then `f6a1c8e4b2d0` drops store entitlement columns.
   - Stop at `e4a9c2d7b1f3`, the revision those three branches grew from.
4. **Flags.** Set `STRIPE_CHECKOUT_ENABLED=false`. Leave `NATIVE_IAP_ENABLED` and `NEXT_PUBLIC_NATIVE_IAP_ENABLED` false. Do not clear `LEGACY_FREE_CUTOFF` on a production service that is still running the new code: an empty value makes production refuse to start.
