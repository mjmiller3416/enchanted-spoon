# Workflow: `hotfix`

**Usage:** `/git hotfix <description>`

Creates a hotfix branch from production (main) for urgent fixes that bypass staging. After merging to main, automatically backports to staging.

## When to Use Hotfix

Use hotfix workflow for:
- ✅ Production-breaking bugs that need immediate fix
- ✅ Security vulnerabilities
- ✅ Critical data issues
- ✅ Major UX blockers affecting users

**Do NOT use for:**
- ❌ Regular bug fixes (use `fix/` branch instead)
- ❌ New features (use `feature/` branch)
- ❌ Non-urgent improvements

## Steps

1. **Validate arguments**
   ```
   /git hotfix auth-token-leak
                ^
                description (kebab-case)
   ```
   - If description missing, ask for it
   - Warn if this could wait for normal workflow

2. **Check git status**
   - If uncommitted changes exist, warn and ask:
     ```
     You have uncommitted changes:
     - Modified: src/components/Header.tsx
     - Untracked: src/utils/helpers.ts

     Options:
     1. Stash changes and continue
     2. Abort and commit first
     ```

3. **Fetch and create branch from main**
   ```bash
   git fetch origin
   git checkout -b hotfix/<description> origin/main
   ```

   > **Critical:** Hotfix branches are based on `main` (production), not `staging`.

4. **Confirm creation**
   ```
   Created hotfix branch: hotfix/auth-token-leak

   Based on: origin/main (abc1234)

   ⚠️  HOTFIX WORKFLOW - This will deploy directly to production

   Next steps:
   1. Make your fix (keep changes minimal)
   2. Test thoroughly
   3. Run `/git commit` to commit with proper format
   4. Create PR to main (will auto-deploy)
   5. After merge, backport to staging
   ```

## Committing the Hotfix

Follow normal commit workflow:
```bash
/git commit
```

Commit format:
```
fix(<scope>): <description>

Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>
```

Example:
```
fix(auth): prevent token leak in error responses

Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>
```

## Creating the Hotfix PR

1. **Push branch and create PR**
   ```bash
   git push origin hotfix/<description>
   gh pr create --base main --head hotfix/<description> --title "Hotfix: <summary>" --body "..."
   ```

   PR body template:
   ```markdown
   ## 🚨 Production Hotfix

   ### Issue
   [Describe the production issue]

   ### Fix
   [Explain the fix]

   ### Risk Assessment
   - Impact: [High/Medium/Low]
   - Scope: [What this changes]
   - Testing: [How it was tested]

   ### Checklist
   - [ ] Fix verified locally
   - [ ] No other side effects
   - [ ] Tested on production-like data
   - [ ] Ready for immediate deploy

   ---
   ⚠️ This will deploy immediately to production via Railway
   ```

2. **Review and merge**
   - Review the PR carefully
   - Merge to main (triggers Railway auto-deploy)

## Backporting to Staging

After the hotfix is merged to main, **you must backport it to staging** to keep branches in sync:

```bash
/git backport
```

This will:
1. Check if staging is behind main
2. Show commits to backport
3. Merge main into staging
4. Push to origin

See [workflows/backport.md](backport.md) for full details.

## Error Handling

**No description provided:**
```
Usage: /git hotfix <description>

Example: /git hotfix auth-token-leak
```

**Branch already exists:**
```
Branch 'hotfix/auth-token-leak' already exists

Options:
1. Switch to existing branch
2. Delete and recreate from main
3. Use different name
```

**Not urgent enough:**
```
⚠️  Hotfix workflow is for production emergencies only.

Is this truly urgent? Consider:
- Will users be actively affected right now?
- Can it wait for normal staging -> main deployment?

If not urgent, use: /git start fix auth-token-leak
```

## Quick Reference

```
Hotfix Flow:
  1. /git hotfix <description>      # Create from main
  2. Make minimal fix
  3. /git commit                     # Commit the fix
  4. Create PR to main               # Deploy to prod
  5. Merge PR                        # Auto-deploy
  6. /git backport                   # Sync to staging
```