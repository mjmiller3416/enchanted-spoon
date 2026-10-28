# Git Workflow Automation

Automate git operations with strict conventions for branches, commits, merges and deploys. No PRs, no approval stops.

## Arguments

$ARGUMENTS

## Instructions

1. Parse the first word of the arguments to determine the workflow
2. Read **only** the matching workflow file from `.claude/skills/git/workflows/`
3. Follow the conventions in `.claude/skills/git/SKILL.md` (branch naming, commit format, co-author line)
4. Execute the workflow steps exactly as documented

## Routing

| Argument | Workflow File | Description |
|----------|---------------|-------------|
| `start <type> <desc>` | `workflows/start.md` | Create a new branch from staging |
| `hotfix <desc>` | `workflows/start.md` | No separate path: start a `fix/` branch; the normal flow ships in minutes |
| `commit [message]` | `workflows/commit.md` | Stage, validate, and commit changes |
| `sync` | `workflows/sync.md` | Rebase current branch onto latest staging |
| `merge` | `workflows/merge.md` | Squash-merge into staging, then fast-forward main (deploys) |
| `deploy` | `workflows/deploy.md` | Fast-forward main to staging (production; no PR) |
| `backport` | `workflows/backport.md` | Bring commits only on main back into staging |
| `cleanup` | `workflows/cleanup.md` | Remove merged/stale branches and close resolved issues |
| _(no args)_ | `workflows/status.md` | Show status and suggest next action |

**Read the workflow file at:** `.claude/skills/git/workflows/<workflow>.md`

**Read conventions at:** `.claude/skills/git/SKILL.md`

Do NOT guess the workflow steps from memory. Always read the specific workflow file first.