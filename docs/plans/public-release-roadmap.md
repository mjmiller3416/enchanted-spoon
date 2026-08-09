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

## Status tracker

| Phase | Focus | Depends on |
|---|---|---|
| [0](#phase-0--reliability--cost-guardrails-do-first) | Reliability & cost guardrails | — |
| [1](#phase-1--monetization-backend) | Monetization (backend) | Phase 0's usage-limit plumbing; a product decision |
| [2](#phase-2--monetization-frontend) | Monetization (frontend) | Phase 1 |
| [3](#phase-3--production-hardening) | Production hardening | — (parallel to 0–2) |
| [4](#phase-4--ui-polish--cleanup) | UI polish & cleanup | — (parallel, lowest urgency) |
| [5](#phase-5--ai-feature-completeness) | AI feature completeness | Phase 0 |

Phases 0 and 3 are the most urgent and don't block on each other — either can start first.
Phase 1 shouldn't start until the **DECISION** item in it is made, since it changes what
gets built.

---

## Known bugs (already filed)

These are tracked in GitHub, not repeated here as line items — linking them into the
phase they belong to so they don't get lost in two places.

- **#131** — Recipes displaying the wrong photo (image_key recurrence). *priority: medium*
- **#132** — Recipe browser filters don't persist across navigation. *priority: medium*
- **#135** — Meal Genie chat recipe generation produces recipes with no ingredients or
  directions. **Root cause found during this audit** — see Phase 0, first item.
- **#136** — Adding a shopping item from mobile creates a duplicate "Other" category.
  Not yet investigated.

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
- [ ] **Add non-empty validation to the shared recipe parser.** (#151)
      `backend/app/services/ai/parse_utils.py:63-94` (`parse_recipe_dict`) and
      `RecipeGeneratedDTO` (`backend/app/dtos/recipe_generation_dtos.py:54-68`) accept an
      empty `ingredients` list and a `None` `directions` as a "successful" parse. This is
      shared by recipe generation, recipe import, and the assistant — fixing it once
      hardens all three call sites, not just the one behind #135.
- [ ] **Add timeout + retry config to the Gemini client.** (#152)
      `backend/app/services/ai/gemini_client.py:39-44` constructs `genai.Client` with no
      `http_options`/`retry_options` — the SDK's default is "never retry" with no bounded
      timeout. A transient Gemini 5xx/429 currently either hard-fails with a raw exception
      string or hangs the request. Pair with an `AbortController`-based timeout on the
      frontend fetch wrapper (`frontend/src/lib/api/base.ts`), which also has none today.
- [ ] **Actually enforce `UserUsage` limits.** (#146)
      `backend/app/services/usage_service.py` writes per-user monthly counters
      (`increment()`) but nothing ever reads them back — `get_usage()` is defined and
      never called. The model's own docstring says these counts are "checked against tier
      limits to enforce rate limiting"; that's aspirational, not implemented. Wire a real
      limit check into each of the 7 AI routes. This is also the prerequisite for Phase
      1's tiered-limits work, so it's worth building generically now rather than twice.
- [ ] **Cap unbounded AI request inputs.** (#153)
      `AssistantRequestDTO.message`/`conversation_history`
      (`backend/app/dtos/assistant_dtos.py:19-20`), image-gen prompts
      (`backend/app/dtos/image_generation_dtos.py:10-11`), and nutrition ingredient lists
      (`backend/app/dtos/nutrition_dtos.py:76`) have no size caps, unlike
      `RecipeGenerationRequestDTO.prompt` which is capped at 500 chars. A client can
      currently inflate per-request token cost arbitrarily.
- [ ] **Fix the 404-becomes-500 bug in ingredients and conversion rules.** (#154)
      `backend/app/api/ingredients.py:134-158` and
      `backend/app/api/conversion_rules.py:143-167` — the `raise HTTPException(404, ...)`
      sits inside the same `try` block whose broad `except Exception` catches it and
      re-raises as a 500. Root cause: unlike every other service in the codebase, neither
      `ingredient_service.py` nor `unit_conversion_service.py` defines domain exceptions
      (project convention per `.claude/CLAUDE.md`). Add them and let the routes catch the
      specific type.
- [ ] **Fix the wrong Gemini API key on nutrition estimation.** (#155)
      `backend/app/services/ai/nutrition_estimation.py:25` reads
      `GEMINI_RECIPE_GENERATION_API_KEY`, not the documented
      `GEMINI_NUTRITION_API_KEY` (`.claude/CLAUDE.md:107`) — the latter is defined in
      `.env` but never referenced anywhere in the backend. Defeats per-feature key/quota
      isolation for this feature specifically.
- [ ] **Add basic rate limiting.** (#156)
      No rate-limiting library or middleware exists anywhere in the backend. At minimum,
      throttle `POST /api/feedback` (creates a real GitHub issue per call — an abuse
      vector against the repo's issue tracker) and
      `POST /api/shopping/external/*` (key-authenticated, but not throttled).

---

## Phase 1 — Monetization (backend)

- [ ] **DECISION: what does "free" actually mean?** Today, `require_pro` gates *all seven*
      AI routers — free users get zero AI access, not a capped allowance. Before building
      anything else here, decide: (a) free stays AI-free and the paid tier is "AI access,
      period," or (b) free gets a small monthly AI allowance and pro raises/removes the
      cap. This changes whether Phase 0's usage-limit plumbing needs to become
      tier-aware or just abuse-aware.
- [ ] **Integrate a payment processor.** The schema already anticipates Stripe
      (`stripe_customer_id` on `User`, `backend/app/models/user.py:57-60`), but there's no
      SDK import, checkout-session creation, or billing-portal link anywhere in the repo.
      Build: checkout session creation endpoint, Stripe customer creation on signup or
      first checkout, customer-portal link generation.
- [ ] **Webhook handler.** Nothing currently ever sets `subscription_tier` to `"pro"` for
      a real (non-admin-granted) user — the only assignment in the entire codebase is the
      `"free"` default at user creation (`backend/app/repositories/user_repo.py:112`).
      Add a signature-verified webhook route that writes `subscription_tier`,
      `subscription_status`, `subscription_ends_at`, and `stripe_customer_id` from
      `checkout.session.completed` / `invoice.paid` / `customer.subscription.updated` /
      `customer.subscription.deleted` events. This is what finally makes the existing
      `has_pro_access` property meaningful for paying users instead of only the admin
      manual-grant path.
- [ ] **If Phase 1's decision is (b):** extend Phase 0's limit-check to branch on tier
      (free gets N/month, pro gets a higher cap or none) instead of the current binary
      `require_pro` gate.
- [ ] **Admin visibility.** `AdminUserListDTO` already surfaces `subscription_tier`/
      `subscription_status` read-only — once real Stripe data exists, confirm it flows
      through correctly, and consider a lightweight usage-by-user view now that
      `UserUsage` is finally being read somewhere (Phase 0).

## Phase 2 — Monetization (frontend)

- [ ] **Pricing page.** No `pricing/` route exists in the `(marketing)` group today, and
      current marketing copy ("Free to use", "Get started free" — `Hero.tsx`,
      `CtaBand.tsx`) doesn't mention a paid tier at all.
- [ ] **Checkout + upgrade flow.** No upgrade button, paywall modal, or "Upgrade to Pro"
      CTA exists anywhere in the app today. "Pro" can currently only be turned on by an
      admin, manually, per user — there's no self-serve path even if a user wanted to pay.
- [ ] **Account/billing settings section.** Settings → Profile shows only Clerk identity
      info. Add plan, renewal date, a usage meter (if Phase 1 goes metered), and a
      "Manage billing" link to the Stripe customer portal.
- [ ] **Graceful 403 handling on AI calls.** `frontend/src/lib/api-client.ts` has only
      generic error handling — a free user hitting any of the 7 pro-gated AI endpoints
      today sees a raw/generic error toast, not an explanation or an upgrade path. Add a
      dedicated paywall-prompt component that intercepts the 403 and offers the upgrade
      flow instead.
- [ ] **Surface the data that's already being fetched.** `useCurrentUser()`
      (`frontend/src/hooks/api/useAdmin.ts:21`) already returns `has_pro_access` and
      `subscription_tier` — today only `is_admin` is ever read from it. Once there's
      somewhere to show it, this is a small change.

---

## Phase 3 — Production hardening

- [ ] **Lock down CORS.** `backend/app/main.py:20-29` defaults `CORS_ORIGINS` to `"*"`
      with `allow_credentials=True` if the env var is unset — Starlette reflects the
      literal request `Origin` back in that configuration, so any origin can make
      credentialed requests. `backend/.env` has no `CORS_ORIGINS` entry, making this an
      easy miss. Set it explicitly to the production frontend origin in Railway.
- [ ] **Fix the hardcoded LAN IP fallback.** `frontend/src/lib/api-client.ts:15`,
      `api-server.ts:12`, and `lib/api/base.ts:3` all fall back to
      `http://192.168.1.213:8000` (a developer's home network) if
      `NEXT_PUBLIC_API_URL` is unset, instead of failing loudly. Same pattern in
      `sitemap.ts`/`robots.ts` falling back to `localhost:3000`.
- [ ] **Add startup config validation.** Nothing currently checks that
      `SQLALCHEMY_DATABASE_URL` points at Postgres rather than silently falling back to a
      throwaway SQLite file (`backend/app/database/db.py:14-17`), or that Clerk keys are
      present — `AuthSettings.is_configured` (`backend/app/core/auth_config.py:51-54`) is
      defined but never called anywhere. Wire it into a startup check, and add an explicit
      guard against `AUTH_DISABLED=true` in a production-looking environment.
- [ ] **Replace the placeholder support email.** `frontend/src/lib/config.ts:5`
      (`support@mealgenie.app`) is live today on the Privacy page, Terms page, and
      marketing footer — there's already a `TODO(launch)` comment sitting right above it.
- [ ] **Turn CI into an actual gate.** `.github/workflows/` currently only has an
      `@claude`-mention responder and an AI PR-review bot — neither runs `pytest` or
      `npm run build`/`lint`. Nothing blocks a PR with new test failures or a broken
      build from merging today.
- [ ] **Add `.env.example` for both `backend/` and `frontend/`** — there's currently no
      single source of truth listing every env var Railway needs.
- [ ] **Fix the SSRF gap in recipe import.** `backend/app/services/ai/recipe_import/service.py:422-453`
      (`_download_image`) fetches a scraped `og:image`/schema.org image URL without
      running it through the same SSRF check (`_validate_url`, lines 148-174) applied to
      the page URL itself. Both HTTP clients also use `follow_redirects=True`, which can
      bypass validation via a redirect even where it is checked.
- [ ] **Cap unbounded list queries.** `recipe_repo.py:424-428` and similar only apply a
      `LIMIT` when the caller passes one — an omitted `limit`/`offset` returns everything.
      Low risk at today's per-user data volumes, but add a sane server-side default before
      the user base grows.
- [ ] *(Lower priority)* security headers (CSP/HSTS/X-Frame-Options) via
      `next.config.ts` or an edge layer; harden the admin SQL console's keyword-denylist
      into an allowlist or point it at a read-only DB role.
- [ ] **Observability** — see [`error-reporting.md`](error-reporting.md); still the
      single largest untracked-here gap (Sentry/GlitchTip not started).

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
- [ ] **Resolve the two deferred URL-prefix renames** noted in
      `backend/app/router.py:64,69` (`/api/ai/meal-genie` → `/api/ai/assistant`,
      `/api/ai/wizard-generation` → `/api/ai/recipe-generation`) — both are marked as
      blocked on coordinated frontend changes.
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
nutrition, recipe generation, ingredients) but **zero coverage** on: `admin_service`/
admin API, `usage_service`, `data_management` (backup/restore/import/export, including
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
