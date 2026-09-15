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
