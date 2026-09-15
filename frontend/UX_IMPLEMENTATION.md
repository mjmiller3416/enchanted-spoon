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
