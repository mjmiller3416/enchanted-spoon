# Workflow: status (`/git`)

1. Gather state:
   ```
   git fetch origin --prune
   git status --short --branch
   git rev-list --left-right --count origin/staging...HEAD
   git rev-list --count origin/main..origin/staging
   git rev-list --count origin/staging..origin/main
   ```
2. Report: current branch, uncommitted changes, commits ahead/behind `origin/staging`, whether `staging` has commits not yet on `main`, and whether `main` has commits `staging` lacks.
3. Suggest one next action:

| State | Suggest |
|---|---|
| Uncommitted changes on `main` or `staging` | Move them to a branch, then `/git commit` |
| Uncommitted changes on a branch | `/git commit` |
| On a feature branch, behind staging | `/git sync` |
| On a feature branch, work committed | `/git merge` (merges and deploys) |
| `staging` ahead of `main` | `/git deploy` |
| `main` has commits staging lacks | `/git backport` |
| Clean and in sync | `/git start <type> <desc>` |
