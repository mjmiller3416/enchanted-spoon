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
