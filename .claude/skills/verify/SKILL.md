---
name: verify
description: How to launch and drive Whiskful locally to verify changes end-to-end (backend + frontend + authenticated browser session).
---

# Verifying Whiskful changes at runtime

## Launch

Backend (auth bypassed; local recipes belong to user_id 2):

```powershell
Set-Location backend
$env:AUTH_DISABLED='true'; $env:DEV_USER_ID='2'
venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

`load_dotenv()` does not override already-set env vars, so setting them
before launch beats `.env` (which has `AUTH_DISABLED=false`).

Frontend: `cd frontend; npm run dev` → http://localhost:3000. Ready in ~2s.

## Getting past Clerk in the browser

The Next.js middleware (`src/proxy.ts`) protects all routes; **sign-ups are
restricted** on the dev instance, so you can't create a throwaway account.
Instead mint a sign-in token with the Clerk backend API (secret key is in
`frontend/.env.local` as `CLERK_SECRET_KEY`):

```powershell
$tok = Invoke-RestMethod -Method Post -Uri 'https://api.clerk.com/v1/sign_in_tokens' `
  -Headers @{ Authorization = "Bearer $sk"; 'Content-Type' = 'application/json' } `
  -Body '{"user_id":"user_38rnkpY7IUPXDhGxJ9U6ukYQ51p","expires_in_seconds":600}'
# user_38rnkpY7... = info@endurance-decking.com (dev owner). List users via GET /v1/users.
```

Then on any app page (e.g. /sign-in), in page JS (Playwright evaluate):

```js
// wait until window.Clerk?.loaded
const res = await window.Clerk.client.signIn.create({ strategy: 'ticket', ticket: TOKEN });
await window.Clerk.setActive({ session: res.createdSessionId });
```

With `AUTH_DISABLED=true` the backend serves DEV_USER_ID's data regardless of
which Clerk user is signed in.

## Gotchas

- Local DB is `backend/app/database/app_data.db` (SQLite). Recipes are owned
  by user_id 2; other users' recipe ids render "Recipe Not Found".
- The recipe print layout (`.print-recipe-content`) is `display:none` on
  screen — use `waitForSelector(..., { state: 'attached' })`, not visible.
- To see the printout, `page.emulateMedia({ media: 'print' })` + screenshot.
  Reset with `emulateMedia({ media: null })`.
- Stub `window.print = () => {}` before driving the Print dialog, or the
  native dialog blocks the session.
- Playwright MCP saves relative screenshot paths to the repo root — clean up.
