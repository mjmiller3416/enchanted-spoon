# Workflow: backport (`/git backport`)

Brings `main` back into `staging` when `main` has commits `staging` lacks
(usually merge commits from old deploy PRs). `/git merge` and `/git deploy`
do this themselves when needed.

1. **Needed?**
   ```
   git fetch origin
   git log --oneline origin/staging..origin/main
   ```
   Empty → nothing to do.
2. **Clean tree**, then:
   ```
   git switch staging
   git pull --ff-only origin staging
   git merge --no-ff origin/main -m "chore: sync main into staging"
   ```
3. **Conflicts:** resolve them. Prefer main's version unless staging has since rewritten that area; then combine. `git add <files>`, `git commit --no-edit`. If you can't resolve one confidently, `git merge --abort` and report.
4. **Test** (from `backend/`: `venv/Scripts/python -m pytest tests -q`; from `frontend/`: `npm run lint`, `npx tsc --noEmit` and `npm test`), then `git push origin staging`.
