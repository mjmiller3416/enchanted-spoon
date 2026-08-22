# Enchanted Spoon Rename Plan

> **Status (2026-08-22): ALL PHASES COMPLETE — plan closed.** Phase 2 (invisible internal IDs)
> executed 2026-08-22 on `staging`, one commit per row: rows 1–8 done, row 9 (Cloudinary) left
> per D3, row 10 (design-sync global) done. Verified live: all five localStorage keys migrate
> with values intact (old keys deleted), the theme blocking script honors the old key pre-
> migration (no flash), and `/api/ai/assistant/*` + the hidden `/api/ai/meal-genie/*` alias
> both serve. **Two scheduled cleanups remain (1–2 releases out): delete the localStorage
> shims (`legacyKey` call sites + `migrateLocalStorageKey` uses) and the legacy route alias
> line in `router.py`.** This is the **final** name change.
>
> **Author's note (2026-08-11):** Drafted ahead of execution so it's ready when you are.

---

## Name history & decision record

| Name | Why it changed |
|------|----------------|
| **Meal Genie** | Original dev name. Never meant for public release; "Meal Genie" is a crowded namespace. |
| **Whiskful** | First rebrand attempt. **Abandoned** — "Whisk" is a live Samsung trademark registered in *exactly* this space (meal-planning / recipe software). Not worth the risk. |
| **Enchanted Spoon** | **Final.** Concept: turning the ordinary (meal planning) into something that feels magical. Design does *not* lean hard into a magic theme — the name carries the whimsy so the UI stays clean. |

### Trademark diligence (summary of user's research, 2026-08)

- **"Enchanted Spoon" (2012 filing)** — DEAD / abandoned (incomplete filing). Confers no rights.
- **"Enchanted Spoon and Co." (registered 2026-07-27)** — the only live mark. Classes:
  - **IC 030** — salsa, honey (physical food products). Not related to software.
  - **IC 035** — online retail store featuring food products. Closest class, but a
    meal-planning *app* is not a retail store — still distinguishable.
  - Our app is software: **IC 009** (downloadable app) and/or **IC 042** (SaaS). Different
    classes. Likelihood-of-confusion is low, and "spoon"/"enchanted" are weak marks in the
    food space (nobody gets broad protection → coexistence is easier).
  - **Watch-item:** they registered recently and are active; monitor for expansion into apps.
- **App stores** — no exact "Enchanted Spoon" match on Apple/Google. Some "Enchanted *"/"* Spoon".
- **Domains** — `enchantedspoon.app` **available** (secure it). `enchantedspoon.com` registered
  but unused, expires ~2026-08-16 — treat as *nice-to-have later*, backorder it; don't plan
  around a drop. `.app` is HSTS-preloaded (HTTPS-forced) — a credibility plus for a web app.

> **This is not a legal clearance.** For a public launch, a short attorney clearance opinion +
> filing our own **intent-to-use (ITU)** application in IC 009 / IC 042 is the step that ends
> the rename-churn pattern. See **Phase 0**.

---

## Guiding principles (read before touching a single file)

The token family **`Whiskful` / `Meal Genie` / `Genie` / `meal-genie`** carries **three distinct
meanings**. A blind find-replace *will* break things. Always classify first:

| Bucket | What it is | Rename target | Where it lives |
|--------|-----------|---------------|----------------|
| **A — Brand** | The app's public name | → **Enchanted Spoon** | User-facing strings, metadata, docs, config |
| **B — Assistant** | The AI character's name (currently **"Genie"**) | → *decision* (keep "Genie", recommended) | Chat UI copy, assistant prompts |
| **C — Internal IDs** | Machine identifiers `meal-genie-*` | → named after *what they are*, not the brand | localStorage keys, API route, Cloudinary folder, backup tag |

**Principles:**
1. **Classify before you replace.** The word "Genie" *never* means the brand — it's always the
   assistant. The `meal-genie-*` kebab tokens are *never* the assistant — they're storage/route IDs.
2. **Internal identifiers are named after what they ARE, not the brand.** The assistant endpoint
   `/api/ai/meal-genie` should become `/api/ai/assistant` — *not* `/api/ai/enchanted-spoon`.
   Arbitrary storage namespaces (Cloudinary folder) can stay as-is forever; users never see them.
3. **User-visible first.** Phase 1 ships independently and is the only phase the market sees.
4. **Never break existing user data.** Every internal-ID rename in Phase 2 needs a migration
   shim (localStorage), a back-compat accept (backups), or a "leave it" decision (Cloudinary).
5. **Route new brand strings through `appConfig.appName`** so this is the *last* painful rename.

---

## Decisions needed before executing (sign-off gates)

- **D1 — Assistant name. ✅ DECIDED (2026-08-11): keep "Genie".** The assistant stays **"Genie"**
  (not reverted to "Meal Genie"). Rationale: "**the** Genie" phrasing already reads naturally
  throughout the UI; it decouples from the crowded "Meal Genie" namespace we're leaving; it's
  already implemented everywhere (zero work); and enchanted ↔ genie share the same "light magic"
  register, so name and assistant reinforce each other. **Consequence for the rename:** the
  assistant name is *out of scope* — Phase 1 changes only the brand word inside assistant prompts
  ("You live inside Whiskful" → "Enchanted Spoon"), never the "Genie" name itself.

- **D2 — Which internal IDs to migrate (Phase 2).** Per-identifier cost/risk table below. Your
  stated intent is "rename everything referring to the app name," but several IDs are invisible
  and costly/risky to change for zero user benefit. Sign off per-row.

- **D3 — Cloudinary folder `meal-genie/`.** **Recommendation: LEAVE IT.** It's an arbitrary
  storage namespace; `docs/RECIPE_IMAGE.md` already documents it as *app-name-independent*.
  Renaming means moving every asset **and** rewriting every stored image URL in the DB — high
  risk, zero user benefit. (Details in Phase 2.)

- **D4 — Genie emoji 🧞 in brand lines.** e.g. `GetStartedCard` "Welcome to Whiskful 🧞".
  When it becomes "Welcome to Enchanted Spoon", swap 🧞 → ✨ / 🥄, or keep 🧞 if the assistant
  stays genie-themed. Cosmetic; decide during Phase 1.

---

## Phase 0 — Legal & priority (do this FIRST, before code)

Protect the name before investing effort in it — you've been burned twice by skipping this.

- [✅] **File an intent-to-use (ITU) trademark application** in **IC 009** and/or **IC 042**
      (software / SaaS). Establishing priority in the *software* class is the highest-value move,
      especially with "Enchanted Spoon and Co." freshly registered in food classes.
- [✅] **Short attorney clearance opinion** confirming the IC 009/042 path is clear vs. the
      IC 030/035 food mark.
- [✅] **Secure `enchantedspoon.app`** (primary domain).
- [✅] **Backorder `enchantedspoon.com`** (drop-catch; don't block launch on it).
- [✅] **Grab social handles** — IG / X / TikTok / etc. — even if unused (squatting prevention).
- [✅] **Provision `info@enchantedspoon.app`** mailbox (replaces `info@whiskful.app`).

---

## Phase 1 — Brand rename (Whiskful → Enchanted Spoon) · USER-VISIBLE · ship first

Everything the user or market sees. One PR, verify against the running app, deploy. Bucket B
(assistant) and Bucket C (internal IDs) are **out of scope** for this phase.

### 1. Central config (single source of truth) ✅
- [x] `frontend/src/lib/config.ts` — `appName: "Whiskful"` → `"Enchanted Spoon"`;
      `supportEmail: "info@whiskful.app"` → `"info@enchantedspoon.app"`; `tagline` kept
      (name-independent).

### 2. Metadata / SEO / PWA ✅
- [x] `frontend/src/app/layout.tsx` — title `default` + `template`, OG `siteName` — all routed
      through `appConfig.appName`.
- [x] `frontend/src/app/manifest.webmanifest` — `name`, `short_name` (hardcoded). `theme_color`
      left unchanged.
- [x] Marketing metadata descriptions:
      `(marketing)/privacy/page.tsx`, `terms/page.tsx`, `whats-new/page.tsx`, `pricing/page.tsx`
      (JSON-LD description) — all via `appConfig.appName`.

### 3. Frontend UI strings — convert hardcoded "Whiskful" → `appConfig.appName` ✅
> All converted to `appConfig.appName` (not just re-labelled) so future renames are one line.
> Bonus: `MarketingHeader.tsx` `aria-label="Whiskful home"` (missed by this list) also fixed.
- [x] `(marketing)/_components/Hero.tsx`
- [x] `(marketing)/pricing/page.tsx` — "Already using Whiskful?" + JSON-LD (no "Whiskful Pro" string was present)
- [x] `components/auth/SignInForm.tsx` — "Sign in to Whiskful"
- [x] `components/auth/SignUpForm.tsx` — "Welcome to Whiskful!"
- [x] `components/common/FeedbackDialog.tsx`
- [x] `(app)/settings/_components/sections/FeedbackSection.tsx` (×2)
- [x] `(app)/settings/_components/sections/AppearanceSection.tsx`
- [x] `(app)/settings/_components/SettingsView.tsx` — version line
- [x] `(app)/dashboard/_components/GetStartedCard.tsx` — "Welcome to {appName} ✨" (**D4** → sparkle)
- [x] `components/common/PaywallDialog.tsx` — "…are part of {appName} Pro."

### 4. Brand visual assets ✅
- [x] New spoon-and-sparkle mark at `frontend/public/logo.svg` (user-provided). `Logo.tsx`
      repointed to `/logo.svg`; old `app-icon.svg`/`name.svg`/`wordmark-horizontal.svg` removed
      (were unused). **Note:** the component had been rendering `app-icon.svg`, not `logo.svg`.
- [x] Favicon, OG/social preview, PWA icons — regenerated from `logo.svg` via `sharp`:
      `src/app/icon.png` (512), `apple-icon.png` (180, white bg), `favicon.ico` (16/32/48),
      `opengraph-image.png` (1200×630 composed banner).
- [x] `.design-sync/previews/Logo.tsx` — wordmark text updated (it's a text mock, not the mark).

### 5. Backend strings ✅
- [x] `backend/app/main.py` — API `title`, `description`, root running-message (×4).
- [x] `backend/app/router.py`, `backend/app/api/__init__.py` — module docstrings.
- [x] `backend/scripts/seed_database.py` — headers/labels (×5).
- [x] `backend/alembic.ini`, `backend/tests/conftest.py` — comment/docstring.
- [x] `backend/.env.example` — `whiskful.app` → `enchantedspoon.app`. (Also `frontend/.env.example`,
      which this list missed; note it's gitignored so the edit is local-only.)
- [x] Assistant prompt brand word: `services/ai/assistant/prompts.py` — "Whiskful" → "Enchanted
      Spoon", **"Genie" kept** (per §5 note / D1).

> **§5 note — assistant prompt brand reference (Bucket A inside Bucket B territory):**
> `backend/app/services/ai/assistant/prompts.py` and `backend/evals/prompts/assistant-system.txt`
> say *"You are **Genie** … You live inside **Whiskful**."* Change **only** the brand word
> ("Whiskful" → "Enchanted Spoon"); **keep the assistant name "Genie"** (unless D1 = rename).
> Also `service.py:134` "I'm Genie" and `generators.py:214` "friendly Genie personality" — leave
> unless D1 changes the assistant name.

### 6. Evals harness (`backend/evals/`) ✅
- [x] `scorecard/*.md`, `README.md`, `package.json` (name → `enchanted-spoon-ai-evals` +
      description), `.env.example`, `scorecard/generate.mjs`, `prompts/assistant-system.txt`
      (Genie kept) — "Whiskful" → "Enchanted Spoon". (`package-lock.json` name also updated but
      it's gitignored → local-only.)

### 7. Docs & agent instructions ✅
- [x] `docs/FRONTEND_DOCUMENTATION.md`, `docs/BACKEND_DOCUMENTATION.md` — titles.
- [x] `.claude/CLAUDE.md`, `AGENTS.md` — the "**Whiskful** is a full-stack…" overview line.
      (Also updated: `.claude/skills/verify/SKILL.md`, `.design-sync/conventions.md`, `NOTES.md`,
      `previews/Sheet.tsx`, `previews/StatCard.tsx`.)
- [x] `docs/RECIPE_IMAGE.md` — **no brand ("Whiskful") mentions present**, so nothing to change
      (its `meal-genie/` refs are Bucket C, left as-is).
- [x] **Left as-is** (honored): `docs/plans/completed/**` and historical `public-release-roadmap.md`
      entries — records of *what was true then*.

### 8. Verification (Phase 1 done-check)
- [x] `grep -ri "whiskful"` returns only intentional records (`docs/plans/**` + a deliberate
      `Logo.tsx` TODO comment).
- [x] Ran the app (2026-08-12): dashboard nav wordmark + new spoon logo render; tab titles
      (`Home · Enchanted Spoon`, `Settings · Enchanted Spoon`, `Pricing · Enchanted Spoon`,
      `Sign in/up · Enchanted Spoon`); settings version line `Enchanted Spoon v0.1.0`; landing/
      pricing/sign-in/sign-up + `manifest.webmanifest` all read "Enchanted Spoon" with **zero
      "Whiskful"**; regenerated `favicon.ico`/`icon.png`/`apple-icon.png`/`opengraph-image.png`
      all serve HTTP 200.
- [x] `npm run lint` + `npx tsc` clean (no new problems from the rename). ⚠️ backend `pytest`
      **not run** — changes are docstrings/strings that can't affect outcomes, and the suite has a
      known pre-broken baseline; `py_compile` of all touched files passed.

---

## Phase 2 — Internal identifier migration (`meal-genie-*`) · INVISIBLE · ship after Phase 1

**EXECUTED 2026-08-22 (branch `staging`, one commit per row).** Rows 1–8 done as specced; row 9
left (D3); row 10 done. Mechanics: a shared `migrateLocalStorageKey` helper + `legacyKey` option
on `useLocalStorageState` handles rows 1–5 (copy old → new on first read, delete old). Row 7's
old prefix is registered as a hidden alias (`include_in_schema=False`) for one release. Row 8
needed no accept-both code — `app_name` is a plain unvalidated `str`, so old backups import
as-is. Live-verified with seeded old keys in the running app (values carried, old keys removed,
no theme flash) and 422-probes against both route prefixes. **Follow-up in 1–2 releases: drop
the localStorage shims and the router alias line.**

None of these are seen by users. Each needs a *deliberate* migration — a blind rename loses user
data or breaks stored URLs. Sign off per row (**D2**).

| # | Identifier | Location(s) | Current → Target | Migration required | Risk if botched | Rec. |
|---|-----------|-------------|------------------|--------------------|-----------------|------|
| 1 | Settings key | `useSettings.ts:101`; `BackupRestore.tsx:117` | `meal-genie-settings` → `enchanted-spoon-settings` | Read-old-write-new shim | **All user settings wiped** | Migrate w/ shim |
| 2 | Theme key | `useSettings.ts:102`; blocking script `layout.tsx:48` | `meal-genie-theme` → `enchanted-spoon-theme` | Shim **+ update blocking script**; keep it in sync | Theme flash / reset on load | Migrate carefully |
| 3 | Recent recipes | `useRecentRecipes.ts:23` | `meal-genie-recent-recipes` → … | Shim (or accept reset) | Recent list clears | Migrate (low risk) |
| 4 | Get-started flag | `useGetStartedProgress.ts:5` | `meal-genie-get-started-complete` → … | Shim (or accept) | Onboarding card reappears | Migrate (low risk) |
| 5 | Chat history | `useChatHistory.ts:11` | `meal-genie-chat-history` → … | Shim | Chat history lost | Migrate w/ shim |
| 6 | Backup filename | `BackupRestore.tsx:66` | `meal-genie-backup-*.json` → `enchanted-spoon-backup-*.json` | None (cosmetic) | — | Rename |
| 7 | API route prefix | `router.py:71`; `lib/api/ai.ts:180,205`; `RECIPE_IMAGE.md` | `/api/ai/meal-genie` → **`/api/ai/assistant`** (feature name, **not** brand) | Coordinated FE+BE; keep old prefix as alias 1 release | In-flight requests 404 | Rename → `assistant` |
| 8 | Backup app tag | `data_management_dtos.py:273` | `app_name = "meal-genie"` → `"enchanted-spoon"` | **Accept both** on import for back-compat | Old backups won't restore | Rename + back-compat |
| 9 | Cloudinary folder | `upload.py:101,173`; `copy_user_recipes.py:59`; `remediate_recipe_image_keys.py`; `backup.py:55 (comment)` | `meal-genie/recipes/…` | Move **all** assets + rewrite **all** stored URLs | Every image 404s | **LEAVE** (D3) |
| 10 | design-sync global | `.design-sync/config.json:5`; `design-sync.entry.tsx` | `MealGenie` / `window.MealGenie` → `EnchantedSpoon` | Dev tooling only | — | Optional |

**Migration shim pattern (localStorage rows 1–5):** on read, if the new key is empty and the
old key exists, copy old → new (then optionally delete old). Keep the shim for ~1–2 releases,
then remove. ⚠️ Per the *theme-model-unified* note: theme = `settings.appearance.theme`; never
resurrect the legacy bare `theme` key while migrating row 2.

**Row 9 rationale (leave Cloudinary):** images are keyed by stable `image_key` (uuid), and the
`meal-genie/` prefix is an arbitrary namespace already documented as app-name-independent.
Renaming buys nothing visible and risks breaking every stored image URL. Skip unless you later
run a full, tested asset-migration (the `remediate_*`/`copy_user_recipes` scripts are the pattern).

**DB verification step:**
- [x] Confirm no literal `meal-genie` / `whiskful` is *stored in the DB schema* (not just code).
      Expected: none except values (backup `app_name`, and `meal-genie/` inside stored image URLs
      — which stay if row 9 = leave). **Verified 2026-08-22:** alembic migrations grep-clean;
      full scan of the dev SQLite (`app/database/app_data.db`) found zero schema hits and, in
      data, only `meal-genie/` inside `recipe.reference_image_path` (158) /
      `banner_image_path` (33) — exactly the row-9 leave case. Prod shares the same migrations,
      so its schema is clean by construction; its only expected value hits are the same
      Cloudinary URLs.

---

## Phase 3 — External systems & operational cutover · coordinate with deploy

Outside the repo. Cross-references the deferred rebrand items in
`public-release-roadmap.md:258–276` — **those `whiskful.app` targets are superseded by
`enchantedspoon.app`.**

**Executed 2026-08-12 via Railway MCP.** Merged `staging`→`main` (`94fe39f9`) — production live
at `enchantedspoon.app` serving Enchanted Spoon (title/OG/site_name verified, backend `/docs` 200).

- [x] **Domain / DNS** — `enchantedspoon.app` was already custom-bound to the Railway `frontend`
      service (no rebind needed); verified serving the new build.
- [x] **Railway env vars** (names unchanged, values updated):
      frontend `NEXT_PUBLIC_APP_URL` → `https://enchantedspoon.app` (was **missing entirely**);
      backend `CORS_ORIGINS` → `https://enchantedspoon.app` (+ railway frontend domain fallback);
      backend `FRONTEND_URL` → `https://enchantedspoon.app` (Stripe redirect base).
      (DB URL left composed from `RAILWAY_PRIVATE_DOMAIN`.)
- [x] **SEO metadata routes** — fixed `robots.ts`/`sitemap.ts` baking the `localhost` fallback
      (Railway doesn't expose `NEXT_PUBLIC_*` to static generation): forced `dynamic`
      (`281cd2c`, merged `d466db1a`). Verified live: both now emit `https://enchantedspoon.app`.
- [x] **Clerk** — production instance created (Frontend API `clerk.enchantedspoon.app`, 5 CNAMEs
      added, DNS + GTS TLS cert verified), dev users copied over, `pk_live`/`sk_live` swapped into
      Railway on both services + 4 `NEXT_PUBLIC_CLERK_*` redirect vars set; rebuilt + verified live
      (2026-08-12). *(optional polish left: app display name + email-template branding)*
- [x] **Stripe** — product renamed → "Enchanted Spoon Pro" + Checkout branding refreshed (user,
      2026-08-22). **`STRIPE_PRICE_ID_PRO` unchanged** (renaming a product doesn't change price
      IDs).
- [x] **Support email** — `info@enchantedspoon.app` live and monitored (mailbox provisioned in
      Phase 0); verified 2026-08-22: zero old-address references anywhere in code — config.ts
      done in Phase 1, backend/GitHub-issue paths grep-clean.
- [x] **Social handles** — N/A (2026-08-22): handles were reserved in Phase 0 but no active
      social accounts exist for the app yet, so there is nothing to rebrand. Brand from day one
      whenever accounts go live.
- [x] **GitHub repo** — renamed `recipe-app` → `enchanted-spoon` (2026-08-22, user reversed the
      earlier "skip" decision). GitHub redirects the old name; Railway's GitHub App auto-updated
      both service sources. `GITHUB_REPO` env updated on Railway backend + local `backend/.env`.
      ⚠️ Never create a new repo named `recipe-app` — it would break the redirects.
      Same day (commit `03a08b67`): npm package name + design-sync `pkg` + preview imports also
      renamed `recipe-app` → `enchanted-spoon`; the `window.MealGenie` global (Phase 2 row 10)
      deliberately left for that phase's decision.
- [x] **OG / preview images & favicon** — new-mark assets from Phase 1 §4 deployed; `og:image`
      resolves to `https://enchantedspoon.app/opengraph-image.png`.

---

## Recommended sequencing

1. **Phase 0** — file ITU + clearance; secure `.app`, handles, mailbox. *(Do first — protect priority before investing.)*
2. **Phase 1** — brand rename PR (+ centralize through `appConfig.appName`); new logo/assets on a
   parallel design track. Verify against the running app → deploy.
3. **Phase 3** — external cutover, coordinated with the Phase 1 deploy (domain, envs, Clerk, Stripe).
4. **Phase 2** — internal-ID migrations, each as its **own commit** with its migration/back-compat.
   Do rows 1–8; leave row 9 (Cloudinary); row 10 optional.
5. **Wrap-up** — update `public-release-roadmap.md` deferred rebrand items; move this doc to
   `docs/plans/completed/` once fully landed.

## Out of scope / explicitly NOT renamed

- The **assistant's name** ("Genie") — unless **D1** says otherwise. Independent of the brand.
- **Historical records** in `docs/plans/completed/**` and past changelog entries.
- **Cloudinary `meal-genie/` folder** (D3) — arbitrary namespace, leave.
- **`meal-genie` as a route/storage token** is being *renamed to what it IS* (e.g. `assistant`),
  not blindly to the brand.
