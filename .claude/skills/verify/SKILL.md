---
name: verify
description: How to launch and drive Enchanted Spoon locally to verify changes end-to-end (backend + frontend + the user's signed-in Chrome session).
---

# Verifying Enchanted Spoon changes at runtime

## Launch

Fresh checkout? Set up first (from repo root):

```bash
cd frontend && npm ci                                   # no node_modules yet
cd ../backend && py -3 -m venv venv && venv/Scripts/python.exe -m pip install -r requirements.txt
venv/Scripts/alembic.exe upgrade head                   # creates/updates app_data.db
```

Backend (auth bypassed; local recipes belong to user_id 2):

```powershell
Set-Location backend
$env:AUTH_DISABLED='true'; $env:DEV_USER_ID='2'
.\venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

Keep the `.\` prefix — without it PowerShell tries to load `venv` as a module
and fails. `load_dotenv()` does not override already-set env vars, so setting
them before launch beats `.env` (which has `AUTH_DISABLED=false`).

Frontend: `cd frontend; npm run dev` → http://localhost:3000. Ready in ~2s.

## Getting past Clerk in the browser

The Next.js middleware (`src/proxy.ts`) protects all routes. **Reuse the
user's own signed-in Chrome session** via Claude in Chrome
(`mcp__claude-in-chrome__*`) — Clerk dev sessions on localhost persist in
Chrome, so after a one-time manual sign-in they carry over between sessions.

1. Open a new tab and navigate to the page under test (e.g. `/shopping-list`).
2. If it lands on the page → signed in, carry on.
3. If it redirects to `/sign-in` → **stop and ask the user** to sign in at
   http://localhost:3000 in that Chrome window themselves, then continue.

**Never** read `CLERK_SECRET_KEY`, mint sign-in tokens via the Clerk API, or
type credentials into the sign-in form. Claude Code's auto-mode classifier
blocks that as credential materialization, and it isn't needed.

With `AUTH_DISABLED=true` the backend serves DEV_USER_ID's data regardless of
which Clerk user is signed in.

## Gotchas

- Local DB is `backend/app/database/app_data.db` (SQLite). Recipes are owned
  by user_id 2; other users' recipe ids render "Recipe Not Found".
- The recipe print layout (`.print-recipe-content`) is `display:none` on
  screen — check it's attached in the DOM, not visible.
- Stub `window.print = () => {}` (via `javascript_tool`) before driving the
  Print dialog, or the native dialog blocks the browser session.
- Close any tabs you opened when done.
