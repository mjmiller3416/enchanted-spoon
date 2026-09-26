# Friends-and-Family Beta Readiness

Completion pass + beta-readiness audit, 2026-09-26. Triggered by the Settings →
Data Management isolation bug (be564dc, "scope data management and ingredient
breakdown to the calling user"): because a bug that severe existed, the audit went
beyond the roadmap to every route, service, and data-modifying flow.

All work below is merged to `staging` (one squash commit per branch). Nothing has
been merged to `main`.

## Audit result in one paragraph

After be564dc, no remaining route lets one signed-in user read or modify another
user's recipes, meals, planner, shopping list, groups, categories, units, rules, or
settings (every one of the ~130 routes was traced into its service and repository).
The serious findings were elsewhere: data-loss paths in restore, broken xlsx import,
an account-takeover path in email relinking, emails published to the public issue
tracker, a server-side file-write route in the frontend, and silent AI quota spend.

## What was fixed (by staging commit)

| Commit | Area | Highlights |
|---|---|---|
| `fix: make restore atomic and repair xlsx import` | Data management | A failed restore rolled back only the reload after the clear had committed → account left empty. Now one transaction. xlsx import never worked (missing `user_id`). Backups now include description/difficulty/source URL, nutrition, group membership, sample flags. Clear-all destroys images only after the DB commit. UI refreshes all caches after delete/restore. |
| `fix: remove unguarded Next.js upload route…` | Security | `frontend/src/app/api/upload/route.ts` (dead code) let any signed-in user write/delete files under `/app/public` via path traversal. Deleted. Backend uploads capped at 15 MB. |
| `fix: keep user emails and raw markup out of public feedback issues` | Privacy | Feedback issues in the **public** repo included the submitter's email. Now `user #<id>`; message rendered inert. |
| `fix: require a Clerk-verified email before relinking accounts` | Auth | Any token with a matching `email` claim could take over an existing account (admins included). Relink now requires Clerk's Backend API to confirm the address is verified on that Clerk user. Concurrent first sign-in no longer 500s. |
| `fix: harden recipe and meal saves…` | Integrity | Duplicate ingredients in one recipe (common from AI/URL import) 500'd; now merged. Input caps match shopping columns. Meal tag validation → 422. No raw SQL in 500 responses. |
| `fix: keep planner, shopping, settings and sample data consistent` | Integrity | "Remove sample data" deleted cooked/favorited/grouped starter content (and streak history). Recipe/meal delete now resyncs the shopping list. Seeded categories are committed. Planner positions no longer collapse to 0. |
| `feat: add self-service account deletion…` | Account | Settings → Account & Profile → Delete Account (cancels Stripe first, deletes data + images, deletes Clerk user). Admin "delete user" always failed; fixed. |
| `fix: close sign-in dead ends…` | Auth UX | Forgot password, two-factor codes, explicit errors for unsupported statuses, `redirect_url` honored. |
| `fix: stop silent AI spend on the menu…` | UX / cost | Opening meals auto-called the metered suggestions API (free tier: 10/month shared). Now on demand. Orphan meals on a full menu cleaned up. Silent settings/shopping failures now toast. `(app)/error.tsx` added. |
| `fix: close SSRF, SQL console, webhook and rate-limit gaps` | Security | Recipe-import resolves DNS and blocks private targets. Admin SQL console is single-statement, read-only transaction, timeout. Late `invoice.paid` can't revive a canceled sub. Rate limits keyed per user (were effectively global behind the proxy). |
| `fix: let migrations build a fresh database…` | Ops | `alembic upgrade head` failed on an empty DB (new environments would crash-loop). Seeder refuses non-SQLite URLs. |

Backend tests: 382 → 451, all passing. Frontend: tsc, lint, vitest (31), and
`next build` pass.

## Manual steps before inviting testers (not code)

1. **Clerk dashboard → disable "Allow users to delete their accounts".** The app now
   hides Clerk's delete control and runs its own deletion (which cancels billing
   first); the dashboard switch closes the door completely.
2. **Confirm `CLERK_SECRET_KEY` is set on the backend service** (staging and prod).
   Email relinking fails closed without it: a user whose Clerk ID changed would get
   a 403 "couldn't be linked" instead of their account. Production startup already
   requires it.
3. **Scrub existing `user-feedback` issues** in the public repo — older ones contain
   a tester's email address. Or point `GITHUB_REPO` at a private repo.
4. **Confirm the staging Railway service has `ENVIRONMENT=production`** (or
   `AUTH_DISABLED=false`). The startup guard only enforces auth when
   `ENVIRONMENT=production`.
5. If testers use SMS/authenticator two-factor, try one sign-in with it on staging;
   the flow is implemented but was verified only by type-check and build (no Clerk
   test instance available to the audit).

## Known issues left for later (not beta-blocking)

- **Observability** (Sentry/GlitchTip) — still not started; see
  [`error-reporting.md`](error-reporting.md). For a small beta, Railway logs plus the
  feedback button are workable.
- **CSP header** — still deferred (needs a Clerk/Cloudinary/API allowlist).
- **DNS rebinding** in recipe import — the guard checks resolved addresses but
  doesn't pin the connection to them.
- **Backups don't include** custom categories/units, conversion rules, or recipe
  groups that have no recipes (these aren't deleted by "Delete All Data" either, so a
  same-account restore keeps them).
- **AI usage caps** check-then-increment, so parallel requests can slightly exceed
  a cap.
- **`scripts/seed_database.py`** inserts rows without `user_id` and fails against the
  current schema (it now also refuses non-SQLite databases).
- Roadmap Phase 4 polish (dead code, raw `<button>`/arbitrary-value sweep) and Phase
  5 decisions ("Import File" coming-soon option, standalone cooking-tip service) are
  unchanged.

### Smaller audit findings (also not beta-blocking)

Frontend:

- **Session ending in another tab** (not verified): `AppLayout` has no signed-out
  guard, so pages may show empty/skeleton states instead of redirecting to sign-in,
  and backend 401s surface as "check your connection"-style errors.
- **Leftover browser storage on shared computers:** legacy unscoped keys
  (`meal-genie-chat-history`, `enchanted-spoon-chat-history`,
  `enchanted-spoon-recent-recipes`, `enchanted-spoon-settings`) are no longer read but
  never removed, and per-account chat history isn't cleared on sign-out.
- **No confirmation on resets:** Settings "Reset Section" and category "Reset to
  Defaults" run immediately (recoverable — the backend only disables custom entries).

Backend:

- **Recipe delete orphans its own Cloudinary images** (`reference_*`/`banner_*` under
  the recipe's `image_key` folder); only "Delete All Data" and account deletion clean
  them up.
- **`DELETE /api/planner/clear`** hard-deletes cleared and completed entries (wiping
  streak history) and orphans transient meals. No UI calls it today.
- **Transient meals aren't cleaned up** when entries are removed by meal
  (`remove_entries_by_meal` in `services/planner/entry.py`).
- **Sample-data seeding is check-then-act:** two concurrent `POST /api/sample-data`
  calls could seed the starter pack twice (user-triggered only).
- **Starter-pack seeding runs inline** in the async `get_current_user` dependency on a
  new account's first request, briefly blocking the event loop for other requests.
- **Model/migration drift:** migrated Postgres has a `fk_recipe_ingredients_recipe_id`
  foreign key the models don't declare the same way (autogenerate reports a
  `remove_fk`). Harmless today; review before the next autogenerated migration.
- **`CLAUDE.md` is inaccurate about ingredients:** it says `Ingredient.user_id` is
  nullable for shared system ingredients, but the column is NOT NULL and every
  ingredient is per-user.
