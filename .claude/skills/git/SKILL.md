---
name: git
description: Follow strict branch naming and commit message conventions for consistent version control
disable-model-invocation: true
---

# Git Workflow Conventions

## Purpose

This skill ensures consistent git practices across the codebase. It defines strict conventions for branch names, commit messages, and PR workflows that Claude should follow automatically when performing any git operations.

## When to Use

- Creating new branches for any work
- Writing commit messages
- Creating pull requests
- Reviewing git history or suggesting git commands

## Workflow Context

This workflow is optimized for **solo development**:

**Solo-friendly practices:**
- Feature branches merge directly to staging (no PR overhead)
- Squash merges keep staging history clean (one commit per feature)
- Force pushes with `--force-with-lease` are safe (you're the only developer)
- Staging → main uses PR as a deployment checkpoint (not for review)

**Prevents common solo developer mistakes:**
- Inconsistent commit messages (enforced conventional commits)
- Wrong branch targeting (validates feature → staging → main flow)
- Uncommitted work on wrong branch (branch-content alignment detection)
- Messy git history (automatic squash merges)
- Lost work from force pushes (warns before destructive operations)

**For team workflows:** This would need adjustment—feature → staging may need PRs for code review, and force pushes require coordination.

## Quick Reference

### Branching Strategy (Solo Workflow)

```
feature/xxx ─┬─► staging ─────► main (production)
fix/xxx     ─┤   (direct)   (PR)     │
chore/xxx   ─┘                       ▼
                              Railway auto-deploy
                                     ▲
hotfix/xxx ──────────────────────────┘
(emergency)      (direct PR)    (then backport to staging)
```

| Branch | Purpose | How to Integrate |
|--------|---------|------------------|
| `main` | Production (auto-deploys) | PR from staging OR hotfix |
| `staging` | Integration/testing | Direct merge from features |
| Feature branches | Development | Squash merge to staging |
| Hotfix branches | Emergency production fixes | PR to main, then backport to staging |

**Solo workflow:** Feature → staging is direct (no PR). Staging → main uses PR for deploy checkpoint.

**Hotfix workflow:** Hotfix branches from main → PR to main → backport to staging.

⚠️ **Never merge feature branches directly to main** (use hotfix for emergencies)

### Branch Format

```
<type>/<description>
```

| Type | Use For | Example |
|------|---------|---------|
| `feature` | New functionality | `feature/shopping-sync` |
| `fix` | Bug fixes | `fix/auth-token-refresh` |
| `hotfix` | **Emergency production fixes** | `hotfix/auth-token-leak` |
| `chore` | Maintenance, deps | `chore/update-deps` |
| `refactor` | Code restructuring | `refactor/api-client` |
| `docs` | Documentation | `docs/api-reference` |
| `test` | Test changes | `test/shopping-integration` |

**Description rules:**
- kebab-case only
- 2-4 words
- No special characters except hyphens

### Commit Format (Conventional Commits)

```
<type>: <description>
```
or with scope:
```
<type>(<scope>): <description>
```

| Type | Meaning | Example |
|------|---------|---------|
| `feat` | New feature | `feat: add shopping sync` |
| `fix` | Bug fix | `fix: resolve auth token refresh` |
| `chore` | Maintenance | `chore: update dependencies` |
| `refactor` | Restructure | `refactor: simplify api client` |
| `docs` | Documentation | `docs: add api docs` |
| `test` | Tests | `test: add sync tests` |
| `style` | Formatting | `style: fix indentation` |
| `perf` | Performance | `perf: optimize query` |

**Commit rules:**
- Type is lowercase
- Description starts lowercase
- No period at end
- Imperative mood ("add" not "added")
- Under 72 characters
- Always include co-author line

### Co-Author Line

All commits must end with:
```
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
```

### PR Title Format

Derive from branch name or summarize commits:
- `feature/shopping-sync` → "Add shopping sync feature"
- `fix/auth-bug` → "Fix auth bug"

### PR Body Template

```markdown
## Summary
- [Key changes in user terms]

## Changes
- [Modified files/areas]

## Test Plan
- [ ] [Testing steps]

---
🤖 Generated with Claude Code
```

## Critical Rules

| Rule | ❌ Wrong | ✅ Correct |
|------|----------|------------|
| Branch type | `bugfix/auth` | `fix/auth-bug` |
| Branch case | `feature/ShoppingSync` | `feature/shopping-sync` |
| Commit type | `FEAT: add feature` | `feat: add feature` |
| Commit mood | `added feature` | `add feature` |
| Commit ending | `feat: add feature.` | `feat: add feature` |
| Commit separator | `feat - add feature` | `feat: add feature` |

## Workflow

### Starting Work

1. Ensure clean working tree or stash changes
2. Fetch latest from origin
3. Create branch:
   - **Normal work:** `/git start <type> <description>` (from staging)
   - **Emergency fix:** `/git hotfix <description>` (from main)

### Committing

1. Stage relevant files (prefer specific files over `git add -A`)
2. Write conventional commit message
3. Include co-author line
4. Use `/git commit` to validate and commit

### Merging to Staging (Solo Workflow)

1. Ensure all changes committed
2. Sync with staging if behind: `/git sync`
3. Merge directly to staging: `/git merge`
4. Branch is squash-merged and deleted

### Deploying to Production

1. Test changes on staging
2. Create deploy PR: `/git deploy`
3. Review and merge PR in GitHub
4. Railway auto-deploys from main

### Emergency Hotfix (Production)

1. Create hotfix branch from main: `/git hotfix <description>`
2. Make minimal fix and commit: `/git commit`
3. Create PR to main (bypasses staging)
4. Merge PR (triggers auto-deploy)
5. **Critical:** Backport fix to staging: `/git backport`

## Related Workflows

- [workflows/start.md](workflows/start.md) - Create branch from staging
- [workflows/hotfix.md](workflows/hotfix.md) - Create emergency fix from main
- [workflows/commit.md](workflows/commit.md) - Stage, validate, and commit
- [workflows/sync.md](workflows/sync.md) - Rebase on latest staging
- [workflows/merge.md](workflows/merge.md) - Squash merge to staging
- [workflows/deploy.md](workflows/deploy.md) - PR from staging to main
- [workflows/backport.md](workflows/backport.md) - Sync hotfixes from main to staging
- [workflows/cleanup.md](workflows/cleanup.md) - Remove merged/stale branches and close resolved issues
- [workflows/pr.md](workflows/pr.md) - Push and create PR
- [workflows/status.md](workflows/status.md) - Show status and suggest action
