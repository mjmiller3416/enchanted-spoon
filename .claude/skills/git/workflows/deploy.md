# Workflow: deploy (`/git deploy`)

Push `staging` to `main` as a fast-forward; Railway deploys production from
`main`. No PR, no approval. `/git merge` runs this at the end of every task;
run it alone to ship whatever is already on `staging`.

1. **Up to date.** Local `staging` must match `origin/staging`:
   ```
   git fetch origin
   git switch staging
   git pull --ff-only origin staging
   ```

2. **What ships.**
   ```
   git log --oneline origin/main..staging
   ```
   Empty → nothing to deploy; stop.

3. **Fast-forward?**
   ```
   git rev-list --count staging..origin/main
   ```
   0 → go on. Anything else means `main` has commits `staging` lacks: run `/git backport`, then come back.

4. **Push.**
   ```
   git push origin staging:main
   ```
   Never add `--force`. Rejected → fetch, merge `origin/main` into `staging`, push `staging`, and retry once. Still rejected → stop and report.

5. **Report.** `git log -1 --oneline origin/main` and that Railway is deploying production. Don't wait for the build unless asked; if asked, check the production site once it's done.

## Rolling back

Revert on a branch and ship it like any other change:
```
git fetch origin
git switch -c fix/revert-<short-name> origin/staging
git revert <squash-commit-sha>
```
Then `/git merge`.
