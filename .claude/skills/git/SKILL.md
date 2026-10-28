---
name: git
description: Branch, commit, merge and deploy workflow for this repo. Every task goes new branch → commit → squash-merge into staging → fast-forward main, with no PRs and no approval stops. Use for any git operation, and when the user types /git.
argument-hint: "[start|commit|sync|merge|deploy|backport|cleanup] [args]"
---

# Git workflow

Solo workflow that runs start to finish without stopping for approval. Every
task, however small:

**new branch → do the task → commit → squash-merge into `staging` → push `staging` to `main`**

No PRs. `main` is production and Railway deploys every push to it; `staging`
deploys to Railway staging. `main` only ever moves by fast-forward to
`staging`, so the two end every task on the same commit.

```
<type>/<desc> ──(squash)──► staging ──(fast-forward push)──► main ──► Railway production
                               │
                               └──► Railway staging
```

## Routing

Read ONLY the matching workflow file, then follow it exactly.

| You typed | Workflow |
|---|---|
| `/git` (no args) | `workflows/status.md` |
| `/git start <type> <desc>` | `workflows/start.md` |
| `/git commit [message]` | `workflows/commit.md` |
| `/git sync` | `workflows/sync.md` |
| `/git merge` | `workflows/merge.md` (merges into staging, then deploys) |
| `/git deploy` | `workflows/deploy.md` (push whatever is on staging to main) |
| `/git hotfix <desc>` | No separate path: `workflows/start.md` with type `fix`. The normal flow reaches production in minutes. |
| `/git backport` | `workflows/backport.md` (when `main` has commits `staging` lacks) |
| `/git cleanup` | `workflows/cleanup.md` |

## Conventions

**Branches:** `<type>/<description>`, kebab-case, 2–4 words, always off
`origin/staging`, always squash-merged back into `staging`.

| Type | Use for |
|---|---|
| `feature` | New functionality |
| `fix` | Bug fix, including urgent production fixes |
| `refactor` | Restructuring |
| `chore` / `docs` / `test` | Maintenance |

**Commits:** Conventional Commits. `<type>(<optional-scope>): <description>`
- Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `style`, `perf`
- Lowercase type and description start, imperative mood, no trailing period, first line ≤ 72 chars.
- Every commit ends with `Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>`. `<Model Name>` is the model actually running the session (from the harness's attribution guidance or the system prompt), never one copied from an old commit.

**Release notes:** user-facing changes get an entry in the in-app "What's new" as part of `/git merge` (step 4). The editorial rules live in `.claude/commands/changelog.md`.

## Hard rules

- **Never stop to ask.** Where a choice comes up, take the default the workflow names and mention it in the summary. The only stops: failing tests you can't fix, a merge conflict you can't resolve confidently, or a push still rejected after fetch-and-merge. Then leave the work committed on its branch and report.
- **Never ship red.** Backend tests, lint, type check and frontend tests must pass before anything merges into `staging`.
- `main` moves only by fast-forward to `staging` (`git push origin staging:main`). Never force-push `main` or `staging`, and never delete `staging` (ruleset `protect-staging-from-deletion` blocks it; don't disable it).
- Always compare `origin/` refs (`origin/main`, `origin/staging`) after `git fetch`; local refs go stale.
- Force-pushing is allowed only on your own feature branch, only with `--force-with-lease`.
- Commands must run in Windows PowerShell 5.1 as well as Git Bash: one git command per line, no `&&`. From WSL, push with `git.exe` (WSL git has no GitHub credentials).

## Checking whether a branch's work is already in a target

Squash merges hide ancestry, so `git branch --merged` and `git branch -d`
can't tell a squash-merged branch is done. Use a trial merge instead:

```
git merge-tree --write-tree origin/staging <branch>
git rev-parse "origin/staging^{tree}"
```

If the first command's first output line equals the second, merging the
branch would change nothing: its work is already in staging, and it is safe
to delete with `git branch -D <branch>`.
