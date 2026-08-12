# Git Workflow Automation

Automate git operations with strict conventions for branches, commits, and pull requests.

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
| `hotfix <desc>` | `workflows/hotfix.md` | Create emergency fix branch from main (production) |
| `commit [message]` | `workflows/commit.md` | Stage, validate, and commit changes |
| `sync` | `workflows/sync.md` | Rebase current branch onto latest staging |
| `merge` | `workflows/merge.md` | Squash merge current branch into staging |
| `deploy` | `workflows/deploy.md` | Create PR from staging -> main (production) |
| `backport` | `workflows/backport.md` | Sync hotfixes from main back to staging |
| `cleanup` | `workflows/cleanup.md` | Remove merged/stale branches and close resolved issues |
| `pr [base-branch]` | `workflows/pr.md` | Push branch and create pull request |
| _(no args)_ | `workflows/status.md` | Show status and suggest next action |

**Read the workflow file at:** `.claude/skills/git/workflows/<workflow>.md`

**Read conventions at:** `.claude/skills/git/SKILL.md`

Do NOT guess the workflow steps from memory. Always read the specific workflow file first.