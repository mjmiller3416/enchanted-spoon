# Workflow: sync (`/git sync`)

Rebase the current typed branch onto the latest `origin/staging`.

1. Refuse on `main` or `staging` (they never get rebased).
2. Uncommitted changes → commit them first if they belong to this task, otherwise use `--autostash`.
3. Check whether it's needed:
   ```
   git fetch origin
   git rev-list --count HEAD..origin/staging
   ```
   0 → already up to date; stop.
4. Note what's incoming (`git log --oneline HEAD..origin/staging`) and what gets replayed (`git log --oneline origin/staging..HEAD`) for the summary, then go on.
5. Rebase:
   ```
   git rebase origin/staging
   ```
   (or `git rebase --autostash origin/staging`).
6. Conflicts → resolve them, `git add <files>` and `git rebase --continue`. If you can't resolve one confidently, `git rebase --abort` and report.
7. Branches normally aren't pushed in this workflow. If this one was, it now needs `git push --force-with-lease`.
