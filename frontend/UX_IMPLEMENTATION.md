# Frontend audit implementation

Target integration branch: `staging`. `main` is the deployment branch and must not be changed or pushed by this work.

## 1. State safety — `codex/frontend-state-safety`

- Recipe detail uses the shared favorite mutation with pending/error feedback.
- Favorite updates use server-confirmed state and serialized writes, avoiding whole-list optimistic rollback.
- Automatic retries are disabled for mutations; queries refresh on reconnect.
- Identity changes remount personal state and retire the previous query cache.
- Personal browser storage is account-scoped. Unowned legacy values are not assigned to the next person signing in; server settings remain authoritative. Theme is device-wide.
- Added Vitest and interaction tests for lost responses, account changes, chat isolation, and favorite persistence.

Validation: 4 regression tests passed; TypeScript, lint, and production build passed. Lint retains the two pre-existing recipe-image warnings. Authenticated browser validation remains pending local sign-in.

## 2. Recipe save safety — `codex/recipe-save-safety`

- Ingredient/notes edits participate in dirty tracking. The wizard uses navigation/unload guards; multiple mounted editors no longer overwrite each other's guard registration.
- Saves retain the created ID and successful uploads so partial failures can be retried without recreating the recipe or repeating successful uploads.
- Changed images replace their checkpoint, and edit upload failures keep the editor open instead of reporting success.
- Successful saves refresh recipe, meal/planner, shopping, and dashboard query families.
- Added failure-injection tests for image uploads and final patch retries, plus unsaved-editor registration/unload checks.

Validation: 10 regression tests, TypeScript, lint, and production build passed.

## Local sign-in recovery — `codex/auth-session-recovery`

The local dev server had been started without outbound network access, preventing Clerk handshakes. Restarted it with network access and started the local authenticated API on port 8000. No authentication bypass or credentials were changed.

- Auth pages redirect an already signed-in user to the dashboard.
- Google sign-in shows pending state and the actual provider error.
- OAuth callback completion uses Clerk's supported callback component.

Validation: 10 regression tests, TypeScript, lint, and production build passed. Browser navigation to `/sign-in` redirected to `/dashboard`, and authenticated API data rendered successfully.

## 3. Settings persistence — `codex/settings-persistence`

- One account-scoped store owns settings and publishes saving/saved/error state.
- Field patches are serialized; local pending edits survive reload and resume on reopening. Delayed responses preserve newer edits. Cross-tab/focus refresh merges around pending fields.
- Versioned backend DTOs normalize legacy theme/clearing values; nested PATCH preserves unrelated fields. The settings service owns commits and requests row locking on supported databases.
- Removed automatic-clear options with no implementation; imports invalidate dependent caches, and backup restore uses the shared settings store.

Validation: 13 frontend regression tests and 74 focused backend tests passed; TypeScript, lint, and production build passed. In the authenticated browser, changing appearance showed “Saving changes…” followed by “All changes saved”; the API confirmed PATCH 200. Restored the original dark preference.

## 4. Feedback and accessibility — `codex/frontend-feedback-accessibility`

- Added shared query-failure/retry presentation for planner, recipe detail, and billing; mutation failures now have visible feedback.
- Numeric inputs support replacement editing, bounded steps, associated labels, forwarded error descriptions/ref, and container focus styling. Autocomplete exposes combobox/option relationships.
- Saved-meal selection and recipe-image actions support keyboard use. Shopping icon actions are named; navigation has nested active states and a skip link.
- Clipboard success is awaited. Recipe deletion loads affected-meal counts and retains confirmation on failure. Checkout-return messaging no longer asserts an unverified subscription state.
- Cook Mode exposes actual wake-lock acquisition/release and handles late acquisition after cancellation.

Validation: 16 frontend tests, TypeScript, lint, and production build passed. Authenticated recipe detail and its action controls rendered successfully. Destructive deletion was not executed against the local account.

## 5. Layout foundation — `codex/frontend-layout-foundation`

- Shared page headers wrap actions and use the existing typography roles.
- Recipe and meal editors share a viewport-aware shell: full-screen on phones, bounded on larger screens, with a scrolling body and visible footer.
- Planner fill height accounts for navigation; the recipe wizard mounts only while open.
- Added UX_DESIGN.md documenting the existing design system and shared composition patterns.

Validation: 16 tests, TypeScript, lint, and production build passed. Inspected editor at 390 and 1440 widths; corrected the default dialog width override. An ingredient-only edit triggered discard protection; discarded the temporary edit and verified the original quantity remained.

## 6. Recipe browsing — `codex/recipe-browsing-polish`

- Date Added sorts real timestamps; missing legacy dates remain last. Card rendering is bounded to 24 per page and resets when the filtered ordering changes.
- Images reset failure/loading state on source replacement, load lazily with asynchronous decoding, and use Cloudinary responsive widths; detail heroes load eagerly.
- Reduced library hero spacing and missing-image detail banners. Secondary detail actions share a menu; phone readers can jump to ingredients/directions. Cached recipe content remains visible if refresh fails.

Validation: 19 frontend tests, TypeScript, lint and production build passed after correcting action-menu markup. Synthetic 5,000-record grid renders 24 cards and advances correctly. Phone detail and print-options dialog verified. Filtering remains on the full existing dataset; server pagination is deferred because the lightweight endpoint lacks filter parity, and local data cannot establish representative network performance.

## 7. Planner and shopping — `codex/planner-shopping-ux`

- Planner has a direct Add meal action, adjacent desktop details, and a phone detail sheet. Labels describe an ordered menu rather than implying scheduled dates.
- Shopping mode is an explicit choice backed by a repeatable PUT; existing cycle endpoint remains compatible. Backend item updates now honor flagged as well as have.
- Checkbox/flag writes send desired values, track pending rows, roll back only their own field, and reconcile after concurrent writes settle. Item deletion no longer restores a whole stale list on failure.
- Compact phone stats, wrapped ingredient names, named checkboxes, and mobile source selection. Hidden editor filters are inert while closed.

Validation: 20 frontend tests (including concurrent failure isolation), 64 focused backend tests, TypeScript, lint and production build passed. Inspected phone planner and meal editor. Local account has no planned meals or shopping items; populated-state interaction coverage comes from isolated tests, with visual review of populated staging data still recommended.

## 8. Dashboard and assistant — `codex/dashboard-assistant-ux`

- Home presents section-level recovery and retains healthy/cached content; onboarding is not inferred from failed requests. Queue labels say Up next and Your planned meals.
- Genie uses a nonmodal desktop dialog and modal expanded/phone dialog with keyboard containment and focus restoration.
- Account-session state owns chat requests, unsent input and generated drafts; closing the popup or changing display size does not discard them. Generated image data stays in memory.

Validation: 22 frontend tests, TypeScript, lint and production build passed. Tested a response arriving after popup closure and dashboard partial failure. Browser verified expanded focus wrapping, return to launcher, unsent close/reopen persistence, and phone layout. Cleared the temporary unsent text; no paid AI request was sent.

## 9. Settings, admin and public polish — `codex/settings-admin-public-polish`

- Settings and admin share section navigation: a compact phone selector and desktop sidebar, with section selection retained in the URL.
- Shared section headers, fewer nested containers, wrapping user rows, and recoverable admin query errors align these views with the rest of the app.
- Profile controls open the authenticated account dialog. Appearance choices use accessible shared buttons; quantity labels reach the actual input.
- Public nutrition copy accurately describes on-demand estimates.

Validation: 22 frontend tests, TypeScript, lint and production build passed (the final input-label forwarding also passed TypeScript, lint and tests). Inspected settings at 390, 768 and 1440 widths in light/dark, verified section reload persistence and account dialog open/close. Original dark theme restored. Local account lacks admin access, so populated admin visual validation remains for staging; access was not bypassed.

## 10. Final recipe submission hardening — `codex/recipe-submit-hardening`

- Submission locks before asynchronous validation so rapid clicks cannot start two saves.
- A lost initial create response or timeout blocks automatic replay and preserves the draft. The editor asks the user to check the library before explicitly allowing another create; partial image/PATCH retries continue using the known recipe ID.

Validation: 25 frontend tests, TypeScript, lint and production build passed. Tests cover lost create responses, explicit retry acknowledgement, confirmed validation rejection and timeout ambiguity. Final focused backend regression run: 86 tests passed (three existing dependency/transaction warnings).

## 11. Navigation integration — `codex/frontend-navigation-hardening`

- Recipe library pages are retained with the account-scoped filters and clamped when results shrink.
- Confirmed navigation invokes dirty editors' discard handlers so persistent overlays close/reset correctly.
- At small desktop widths the app uses compact navigation. Inactive pinned controls are unmounted, and active controls have space without pushing account actions out of view. Active navigation exposes aria-current.
- Public phone header uses the logo without the full wordmark to prevent sign-in controls overlapping. Pricing language describes recipe nutrition facts and queue-based meal planning accurately.

Validation: 27 frontend tests passed, including restored pagination, shrinking collections and selective discard handlers. TypeScript, lint and production build passed before the final small public-header/copy adjustment; final lint/build rechecked for that adjustment. Browser confirmed the repaired 1024px app header and inspected 360px profile layout.

## Staging review notes and verification limits

All changes use the existing semantic design system; no rebrand or backend architecture overhaul. Each feature was tested before its staging merge. Targeted backend integration coverage totals 86 passing tests. Frontend coverage totals 27 passing tests, plus type checking, lint and production builds.

Runtime review covered authenticated home, library/detail/print controls, recipe/meal editors, empty planner/shopping, settings, assistant, profile management and public pricing across phone/tablet/desktop sizes. Local sign-in now works with the authenticated backend; authentication was not bypassed.

Still requiring populated staging review:
- Local account has one recipe and no planned meals/shopping items, and is not an admin. Populated planner/shopping behaviors have isolated test coverage, but populated admin tables and realistic long-content visual coverage are incomplete.
- Large-collection rendering is tested with 5,000 synthetic records; representative network performance and server browse pagination are deferred.
- The in-app browser did not apply keyboard zoom shortcuts, so actual 200% browser zoom remains unverified. Full rendered contrast, system-theme/reduced-motion and every network/account-switch combination were not exhaustively exercised.
- No live paid AI request, checkout, destructive recipe deletion, or account-security change was performed. Failure cases use focused tests where available.
- Visual checks were inspected during implementation; a complete archived before/after screenshot set was not produced.

The remaining matrix is review work, not evidence of a passing full end-to-end suite. Existing build warnings about multiple lockfiles/browser-baseline data and three backend dependency/transaction warnings remain.
