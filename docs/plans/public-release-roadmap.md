# Public Release Roadmap

Status snapshot from a full-codebase audit, August 2026. Not a build prompt — read each
phase's checklist before starting it, since some items need a product decision (marked
**DECISION**) before they're actionable engineering work.

> **Where this fits:** [`error-reporting.md`](error-reporting.md) already tracks the
> observability gap (Sentry/GlitchTip) in detail — it isn't duplicated here, just
> referenced in Phase 3. The five research passes behind this doc covered frontend,
> backend, the AI module, monetization infrastructure, and production/ops readiness.

## Where things actually stand

The core product — recipes, meal planning, shopping lists — is in good shape: clean
layered architecture, consistent ownership checks, decent test coverage on the main
services, and a design system that's followed more often than not. This is not a
pre-alpha; the app already has real users (the shopping-ingest integration pushes to a
live account, and the two `user-feedback`-labeled GitHub issues came from someone's
phone).

Three gaps stand between here and a public free/paid launch, in order of how much they'd
hurt if ignored:

1. **AI costs are completely unmetered.** Every Gemini-backed endpoint is gated only by a
   binary "is this account pro" check — nothing caps how many times a account can call
   it. This is real, uncapped external spend today, not just a launch blocker.
2. **Monetization is a database column, not a feature.** `subscription_tier` exists on
   the `User` model and is checked everywhere access matters, but nothing in the codebase
   ever sets it to `"pro"` except an admin's manual override. There is no payment
   processor integration anywhere.
3. **Production hardening basics are unfinished** — CORS defaults wide open, a frontend
   config fallback points at a developer's home LAN IP, there's no CI gate, and the
   support email on the live Privacy/Terms pages is still a placeholder.

> **Update 2026-08-09:** gaps 1 and 2 are now closed in production — AI usage is metered
> (Phase 0 deployed), and the full Stripe backend (checkout, portal, webhook sync) is live
> in test mode with the $4.99/mo Pro price configured. Gap 3 (hardening) remains the main
> open front alongside the Phase 2 upgrade-flow UI.
>
> **Update 2026-08-09 (later):** Phase 2 is code complete — pricing page, paywall/429
> interception, billing settings with usage meter, self-serve checkout, and the metered
> free tier (#164) are built and verified locally against real Stripe test mode. Deploy,
> then run one prod test-mode checkout to close #165.
>
> **Update 2026-08-09 (Phase 3):** most of gap 3 is now closed in code — CORS default no
> longer combines wildcard + credentials, the home-LAN-IP fallback is gone, recipe-import
> SSRF is hardened (image URL validated + redirects re-checked), list queries have a
> server-side cap, startup config validation fails fast in production, the support email is
> real (`info@whiskful.app` — app rebranding to **Whiskful**), security headers ship via
> `next.config.ts`, `frontend/.env.example` exists, and a CI workflow gates the build.
> Deferred: observability (Sentry/GlitchTip) and a full app-name rebrand.

## Status tracker

| Phase | Focus | Depends on | Status (2026-08-09) |
|---|---|---|---|
| [0](#phase-0--reliability--cost-guardrails-do-first) | Reliability & cost guardrails | — | ✅ Complete, deployed |
| [1](#phase-1--monetization-backend) | Monetization (backend) | Phase 0's usage-limit plumbing; a product decision | ✅ Complete (#164/#166 + #165 verification moved to Phase 2) |
| [2](#phase-2--monetization-frontend) | Monetization (frontend) | Phase 1 | 🔶 Code complete 2026-08-09 (#164/#166 done, verified locally) — deploy + one prod checkout closes #165 |
| [3](#phase-3--production-hardening) | Production hardening | — (parallel to 0–2) | 🔶 Most items done 2026-08-09 (CORS default, LAN-IP fallback, SSRF, query caps, startup validation, support email, CI, env examples, security headers); observability deferred |
| [4](#phase-4--ui-polish--cleanup) | UI polish & cleanup | — (parallel, lowest urgency) | Not started |
| [5](#phase-5--ai-feature-completeness) | AI feature completeness | Phase 0 | Not started |

Phases 0 and 3 are the most urgent and don't block on each other — either can start first.
Phase 1 shouldn't start until the **DECISION** item in it is made, since it changes what
gets built.

---

## Known bugs (already filed)

These are tracked in GitHub, not repeated here as line items — linking them into the
phase they belong to so they don't get lost in two places.

All four are now **fixed and closed** (kept for the record):

- ~~**#131** — Recipes displaying the wrong photo (image_key recurrence).~~ ✅
- ~~**#132** — Recipe browser filters don't persist across navigation.~~ ✅ (via #147)
- ~~**#135** — Meal Genie chat recipe generation produces recipes with no ingredients or
  directions.~~ ✅ (Phase 0, first item)
- ~~**#136** — Adding a shopping item from mobile creates a duplicate "Other" category.~~ ✅ (via #148)

New user-feedback bugs since (open): **#171** (planner drag-and-drop delay), **#172**
(shopping-toggle tooltip), **#173** (shopping list toggle, cannot replicate).

---

## Phase 0 — Reliability & cost guardrails (do first)

Not launch-prep — these protect the app *today*, independent of the monetization
timeline, and one of them is a diagnosed fix for an open bug.

- [✅] **Fix the assistant's fake-success recipe bug (closes #135).**
      `backend/app/services/ai/assistant/generators.py:251-265` — `_generate_recipe_from_args`
      catches *any* failure from the recipe-generation call (network error, malformed
      Gemini JSON, a Pydantic validation error) and silently falls through to
      `return RecipeGeneratedDTO(recipe_name=..., ingredients=[])` — no directions, no
      error signal. The caller (`generators.py:45-53`) then unconditionally returns a
      cheerful "Here's your recipe! 🎉" regardless of whether it's empty. Nothing
      downstream (chat UI, wizard prefill, Zod schema) checks for emptiness before
      presenting it as done. Fix: let real failures surface as real errors instead of a
      fabricated empty recipe.
- [✅] **Add non-empty validation to the shared recipe parser.** (#151)
      `backend/app/services/ai/parse_utils.py:63-94` (`parse_recipe_dict`) and
      `RecipeGeneratedDTO` (`backend/app/dtos/recipe_generation_dtos.py:54-68`) accept an
      empty `ingredients` list and a `None` `directions` as a "successful" parse. This is
      shared by recipe generation, recipe import, and the assistant — fixing it once
      hardens all three call sites, not just the one behind #135.
- [✅] **Add timeout + retry config to the Gemini client.** (#152)
      `backend/app/services/ai/gemini_client.py:39-44` constructs `genai.Client` with no
      `http_options`/`retry_options` — the SDK's default is "never retry" with no bounded
      timeout. A transient Gemini 5xx/429 currently either hard-fails with a raw exception
      string or hangs the request. Pair with an `AbortController`-based timeout on the
      frontend fetch wrapper (`frontend/src/lib/api/base.ts`), which also has none today.
- [✅] **Actually enforce `UserUsage` limits.** (#146)
      `backend/app/services/usage_service.py` writes per-user monthly counters
      (`increment()`) but nothing ever reads them back — `get_usage()` is defined and
      never called. The model's own docstring says these counts are "checked against tier
      limits to enforce rate limiting"; that's aspirational, not implemented. Wire a real
      limit check into each of the 7 AI routes. This is also the prerequisite for Phase
      1's tiered-limits work, so it's worth building generically now rather than twice.
- [✅] **Cap unbounded AI request inputs.** (#153)
      `AssistantRequestDTO.message`/`conversation_history`
      (`backend/app/dtos/assistant_dtos.py:19-20`), image-gen prompts
      (`backend/app/dtos/image_generation_dtos.py:10-11`), and nutrition ingredient lists
      (`backend/app/dtos/nutrition_dtos.py:76`) have no size caps, unlike
      `RecipeGenerationRequestDTO.prompt` which is capped at 500 chars. A client can
      currently inflate per-request token cost arbitrarily.
- [✅] **Fix the 404-becomes-500 bug in ingredients and conversion rules.** (#154)
      `backend/app/api/ingredients.py:134-158` and
      `backend/app/api/conversion_rules.py:143-167` — the `raise HTTPException(404, ...)`
      sits inside the same `try` block whose broad `except Exception` catches it and
      re-raises as a 500. Root cause: unlike every other service in the codebase, neither
      `ingredient_service.py` nor `unit_conversion_service.py` defines domain exceptions
      (project convention per `.claude/CLAUDE.md`). Add them and let the routes catch the
      specific type.
- [✅] **Fix the wrong Gemini API key on nutrition estimation.** (#155)
      `backend/app/services/ai/nutrition_estimation.py:25` reads
      `GEMINI_RECIPE_GENERATION_API_KEY`, not the documented
      `GEMINI_NUTRITION_API_KEY` (`.claude/CLAUDE.md:107`) — the latter is defined in
      `.env` but never referenced anywhere in the backend. Defeats per-feature key/quota
      isolation for this feature specifically.
- [✅] **Add basic rate limiting.** (#156)
      No rate-limiting library or middleware exists anywhere in the backend. At minimum,
      throttle `POST /api/feedback` (creates a real GitHub issue per call — an abuse
      vector against the repo's issue tracker) and
      `POST /api/shopping/external/*` (key-authenticated, but not throttled).

---

## Phase 1 — Monetization (backend)

- [✅] **DECISION: what does "free" actually mean?** (#161) **Resolved 2026-08-09: option (b),
      metered free** — free gets a small monthly AI allowance; don't enable free caps until
      the Phase 2 upgrade flow exists. Original framing: Today, `require_pro` gates *all seven*
      AI routers — free users get zero AI access, not a capped allowance. Before building
      anything else here, decide: (a) free stays AI-free and the paid tier is "AI access,
      period," or (b) free gets a small monthly AI allowance and pro raises/removes the
      cap. This changes whether Phase 0's usage-limit plumbing needs to become
      tier-aware or just abuse-aware.
- [✅] **Integrate a payment processor.** (#162) **Done 2026-08-09 (PR #168, deployed):**
      checkout session + customer creation + billing portal endpoints live at `/api/billing/*`.
      Stripe test-mode env fully configured (product, $4.99/mo price, Railway env vars).
      Original framing: The schema already anticipates Stripe
      (`stripe_customer_id` on `User`, `backend/app/models/user.py:57-60`), but there's no
      SDK import, checkout-session creation, or billing-portal link anywhere in the repo.
      Build: checkout session creation endpoint, Stripe customer creation on signup or
      first checkout, customer-portal link generation.
- [✅] **Webhook handler.** (#163) **Done 2026-08-09 (PR #169, deployed):** signature-verified
      `/api/webhooks/stripe` handles all four events; verified end-to-end in prod (signed
      test event → tier flipped). Original framing: Nothing currently ever sets `subscription_tier` to `"pro"` for
      a real (non-admin-granted) user — the only assignment in the entire codebase is the
      `"free"` default at user creation (`backend/app/repositories/user_repo.py:112`).
      Add a signature-verified webhook route that writes `subscription_tier`,
      `subscription_status`, `subscription_ends_at`, and `stripe_customer_id` from
      `checkout.session.completed` / `invoice.paid` / `customer.subscription.updated` /
      `customer.subscription.deleted` events. This is what finally makes the existing
      `has_pro_access` property meaningful for paying users instead of only the admin
      manual-grant path.
- [✅] **Admin visibility.** (#165) **Usage-by-user view shipped 2026-08-09** (`GET
      /api/admin/usage` + "AI Usage" admin tab with month navigation and used/limit cells).
      The final verification step (real checkout → admin list renders Stripe-driven
      values) moved to Phase 2, where the checkout UI it depends on gets built.

**Phase 1 is complete.** Its two remaining items — #164 (tier-aware free caps) and #166
(cap-hit 429 UX) — were moved into Phase 2 (2026-08-09) because both depend on the
upgrade flow existing: free caps shouldn't activate until a capped user has an upgrade
button to click, and the 429 UX shares one interception layer with the Phase 2 paywall.

## Phase 2 — Monetization (frontend)

**Code complete 2026-08-09** — everything below built and verified locally end-to-end
(sign-in as free user → 429 → paywall dialog → checkout session → Stripe-hosted test
page → cancel return to Settings → Plan & Billing). Only the post-deploy prod checkout
run remains (last item).

- [✅] **Pricing page.** `(marketing)/pricing` route: Free vs Pro ($4.99/mo) cards,
      linked from the marketing header + footer, added to `sitemap.ts` and the public
      routes in `proxy.ts`. CtaBand copy updated from "Free to use" to "Free to start"
      with a Pro/pricing mention.
- [✅] **Checkout + upgrade flow.** "Upgrade to Pro — $4.99/mo" buttons in the paywall
      dialog and Settings → Plan & Billing, both driving `POST
      /api/billing/checkout-session` → Stripe-hosted Checkout
      (`hooks/api/useBilling.ts`). Return params `?checkout=success|cancelled` land on
      the billing tab with a toast; success invalidates the cached profile/usage.
- [✅] **Account/billing settings section.** New Settings → Plan & Billing category
      (`sections/BillingSection.tsx`): plan badge, renewal date
      (`subscription_ends_at`, now on `CurrentUserDTO`), per-feature usage meter
      (new `GET /api/users/me/usage`), Upgrade CTA for free users, "Manage billing" →
      Stripe portal for subscribers.
- [✅] **Graceful 403 + 429 handling on AI calls** *(closes #166)*. ONE interception
      layer in `lib/paywall.ts`: React Query mutations are caught globally via
      `MutationCache.onError` (QueryProvider); the wizard's direct generate/import calls
      and the assistant chat call it explicitly. 403 pro-required → upgrade paywall
      dialog; 429 `usage_limit_exceeded` → "used this month's allowance (x/X), resets
      next month" with upgrade CTA for free users (plain notice for capped pro users).
      Also fixed `fetchApi`/`apiFetch` turning structured 429 detail objects into
      `[object Object]` error messages.
- [✅] **Enable the metered free tier** (#164). `require_within_usage_limit` now depends
      on `get_current_user` instead of `require_pro` — free users fall through to the
      tier-cap check. Taste-test caps in `TIER_USAGE_LIMITS`: 3 images / 10 suggestions
      (shared by 4 features) / 10 assistant messages / 5 imports per month. Covered by
      `tests/test_metered_free_tier.py` (free under/at cap, pro, admin exempt, usage
      endpoint).
- [🔶] **Final Stripe verification** (#165 remainder). Local end-to-end passed: checkout
      session created from the paywall, Stripe customer persisted
      (`stripe_customer_id` written), cancel path returns to the billing tab. The admin
      Users list now renders `subscription_ends_at` ("renews {date}") next to the tier
      badge. **Remaining (needs this code deployed):** one real test-mode checkout in
      prod through the upgrade flow → confirm the webhook flips the tier and the admin
      list shows the Stripe-driven values. Then close #165.
- [✅] **Surface the data that's already being fetched.** `subscription_tier` /
      `has_pro_access` / `subscription_status` / `subscription_ends_at` now render in
      Settings → Plan & Billing and the admin Users list.

---

## Phase 3 — Production hardening

- [✅] **Lock down CORS.** `backend/app/main.py` no longer defaults to
      `allow_credentials=True` alongside a wildcard origin. Origins are now parsed with
      whitespace stripped, and `allow_credentials` is only enabled when specific origins
      are configured (`allow_credentials = CORS_ORIGINS != ["*"]`) — superseding the old
      `origin/hotfix/cors-credentials-conflict` partial fix. **Railway prod already has
      `CORS_ORIGINS` set to the frontend origin (verified 2026-08-09).** *Remaining manual
      step: delete the now-stale `origin/hotfix/cors-credentials-conflict` remote branch.*
- [✅] **Fix the hardcoded LAN IP fallback.** `frontend/src/lib/api-client.ts`,
      `api-server.ts`, and `lib/api/base.ts` now fall back to `http://localhost:8000` (the
      documented dev default) instead of a developer's home network IP. `sitemap.ts` /
      `robots.ts` keep their `localhost:3000` fallback intentionally — that's the
      documented `NEXT_PUBLIC_APP_URL` dev default, not a leaked private address.
- [✅] **Add startup config validation.** New `backend/app/core/startup.py` (`validate_config`,
      wired into a FastAPI `lifespan`). In a production environment (`ENVIRONMENT=production`)
      it aborts startup if `AUTH_DISABLED=true`, if Clerk isn't configured
      (`AuthSettings.is_configured`), or if `SQLALCHEMY_DATABASE_URL` still points at SQLite;
      in dev it logs the same conditions as notices. `ENVIRONMENT` added to `backend/.env.example`.
- [✅] **Replace the placeholder support email.** `frontend/src/lib/config.ts` now uses
      `info@whiskful.app` (rebrand to **Whiskful**; domain purchased 2026-08-09) and the
      `TODO(launch)` comment is removed. *Note: the full app-name rebrand (page titles,
      OG tags, backend API title, marketing copy, changelog) was completed 2026-08-10;
      the AI assistant is now "Genie" and the internal `meal-genie-*` identifiers were
      deliberately kept. The remaining launch-gated DNS/env switch is the next item.*
- [✅] **Cut the public domain over.** *Superseded and executed 2026-08-12 — the app
      launched at **`https://enchantedspoon.app`**, not `whiskful.app` (the Whiskful name
      was dropped over a Samsung trademark; see
      `docs/plans/completed/enchanted-spoon-rename.md`). Every value switch this item
      described was applied with the new domain: frontend `NEXT_PUBLIC_APP_URL`, backend
      `CORS_ORIGINS` + `FRONTEND_URL`, Clerk production instance at
      `clerk.enchantedspoon.app`, Stripe product renamed "Enchanted Spoon Pro"
      (2026-08-22, `STRIPE_PRICE_ID_PRO` unchanged), DNS custom-bound on Railway.*
- [🔶] **Turn CI into an actual gate.** New `.github/workflows/ci.yml`: a **backend** job
      (Python 3.11, `pytest`) and a **frontend** job (Node 20, `npm run lint` + `npm run
      build`). `npm run build` is the hard gate. pytest and lint are `continue-on-error`
      (report-only) for now because both have a known pre-existing baseline of failures
      (33 async-mock tests; 9 react-hooks lint errors) — drop `continue-on-error` on each
      once its baseline is cleared to make it a hard gate.
- [✅] **Add `.env.example` for both `backend/` and `frontend/`.** `frontend/.env.example`
      added (mirrors `.env.local`, secrets blanked); `backend/.env.example` landed earlier
      with #168.
- [✅] **Fix the SSRF gap in recipe import.** `_download_image` now runs the scraped image
      URL through `_validate_url` before fetching. Both HTTP clients switched to
      `follow_redirects=False`; a shared `_fetch_following_validated_redirects` helper
      follows redirects manually (capped at `MAX_REDIRECTS=5`), re-validating every hop so
      a 3xx `Location` can't bounce the request to a private/loopback host. *(DNS-rebinding
      — a hostname that resolves to a private IP — is still out of scope; the guard checks
      IP literals and redirect targets, not resolved DNS.)*
- [✅] **Cap unbounded list queries.** `recipe_repo.filter_recipes`, `meal_repo.filter_meals`,
      and `shopping/aggregation_repo.search_shopping_items` now apply a `MAX_LIST_ROWS = 1000`
      backstop when the caller omits `limit`, instead of returning the whole table.
- [🔶] *(Lower priority)* **Security headers** added via `next.config.ts` `headers()`:
      `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, HSTS,
      `Permissions-Policy`. **CSP intentionally deferred** — it needs a careful allowlist
      for Clerk/Cloudinary/the API origin. Still open: harden the admin SQL console's
      keyword-denylist into an allowlist or point it at a read-only DB role.
- [ ] **Observability** *(deferred to a dedicated follow-up, 2026-08-09)* — see
      [`error-reporting.md`](error-reporting.md); still the single largest untracked-here
      gap (Sentry/GlitchTip not started).

---

## Phase 4 — UI polish & cleanup

Lower urgency than 0–3; batch this whenever there's a slow week.

- [ ] **Dead code removal:** `frontend/src/components/common/IconButton.tsx` (orphaned,
      zero imports, and non-compliant — uses a raw `<button>` internally); unused shadcn
      primitives `accordion.tsx`, `multi-select.tsx`, `scroll-area.tsx`; deprecated
      constant arrays in `frontend/src/lib/constants.ts:18-32,71-85`; stray leftover empty
      route directories from the route-groups migration (`app/dashboard/`, `app/recipes/`,
      etc. — superseded by `(app)/...`); a stray debug comment in `constants.ts:2`.
- [ ] **Design-system sweep.** Raw `<button>` instead of `<Button>` clusters in ~18 files
      (worth prioritizing the theme picker in `AppearanceSection.tsx:63` and the
      method-selection cards in `MethodSelectionStep.tsx:72` — primary interactive
      controls, not edge cases); arbitrary Tailwind bracket values (`h-[...]`,
      `min-h-[...]`) across ~19 files.
- [ ] **Fix broken "Manage Profile" links.** `ProfileSection.tsx:107,155` opens Clerk's
      generic marketing domain (`accounts.clerk.com/user`) instead of the actual
      instance account portal — should use Clerk's `openUserProfile()` /
      `<UserProfile/>`.
- [ ] **Add an account-deletion flow.** Settings currently only deletes app data
      (recipes/meals/lists), not the account itself — a real gap for a public consumer
      launch (GDPR/CCPA-adjacent expectation).
- [ ] **Add per-route `error.tsx` boundaries** for the main app routes (recipes,
      meal-planner, shopping-list) — today only a root boundary exists, so a failure deep
      in one feature loses page context. (Per-route `loading.tsx` already exists
      everywhere — this is just the error-boundary half.)
- [ ] **Small a11y fixes:** add `aria-pressed` to the `AppearanceSection` theme-picker
      buttons (the method-selection wizard step already does this correctly — same
      pattern, just missing here); a targeted keyboard-nav pass on the recipe wizard
      stepper and the drag-and-drop ingredient/category reordering.

## Phase 5 — AI feature completeness

- [ ] **DECISION: ship or cut the "Import File" recipe-creation method.** Permanently
      `isAvailable: false` with a "Coming Soon" badge in the wizard
      (`MethodSelectionStep.tsx:36,63,100`) — dead option in a launch-facing flow either
      way.
- [ ] **DECISION: ship or cut the standalone Cooking Tip service.** Fully built on the
      backend (category rotation, dedup logic) and defined in the frontend API client,
      but nothing calls it — no hook, no UI. (Not to be confused with `AISuggestions.tsx`,
      which uses a *different* dish-specific tip field from the meal-suggestions service.)
- [ ] **Resolve the remaining deferred URL-prefix rename**:
      `/api/ai/wizard-generation` → `/api/ai/recipe-generation` (`router.py` TODO,
      blocked on a coordinated frontend change). The other one —
      `/api/ai/meal-genie` → `/api/ai/assistant` — was done 2026-08-22 in the Phase 2
      rename; the old prefix is aliased for one release, then delete the alias line in
      `router.py`.
- [ ] **Harden function-call handling.** `assistant/generators.py:59-60` — if Gemini
      calls a tool name outside the three declared ones, the dispatcher returns a
      response that makes the chat UI show nothing at all (the user's turn silently
      vanishes). Also only the *first* function call across all response parts is
      captured (`assistant/service.py:174-186`); a parallel/multiple function-call
      response would silently drop the rest.
- [ ] **Clean up stale bytecode** from an apparently-removed `assistant_suggestions`
      service and a removed assistant streaming feature
      (`backend/app/services/ai/assistant_suggestions/__pycache__/*`,
      `assistant/__pycache__/streaming.cpython-314.pyc` — no matching `.py` source
      exists for either).

---

## Test coverage gaps (reference, not a phase)

Backend has real pytest coverage on the main services (recipes, meals, planner,
nutrition, recipe generation, ingredients) — plus, as of 2026-08-09: `usage_service`,
the Stripe webhook service, and the admin usage endpoint. Still **zero coverage** on:
the rest of `admin_service`/admin API, `billing_service`, `data_management` (backup/restore/import/export, including
the destructive clear-all/restore endpoints), `upload.py`, `recipe_import` (notably the
file with the SSRF-guard logic from Phase 3), `image_generation`, `cooking_tips`,
`meal_suggestions`, core shopping aggregation/sync logic, the `user_*` settings services,
auth dependencies/JWKS, and `github_service`. Worth prioritizing `recipe_import` and
`usage_service` given Phase 0/3 work touches both.

Frontend has **no automated tests at all** — no Jest/Vitest/Playwright/Cypress config,
no `*.test.ts(x)` files anywhere, and no `test` script in `package.json`. Not blocking a
launch by itself, but worth at least a handful of Playwright smoke tests
(sign-up → recipe → meal plan → shopping list) before relying on manual QA at public
scale.
