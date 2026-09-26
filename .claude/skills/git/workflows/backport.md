# Workflow: `backport`

**Usage:** `/git backport`

Syncs hotfixes from main back to staging after a production deployment. Use this after merging a hotfix PR to main, or when staging has fallen behind main.

## When to Use Backport

```
Your situation:
main:     A -> B -> C -> D  <-- (hotfix merged here)
               \
staging:        E -> F      <-- (missing the hotfix)

After /git backport:
main:     A -> B -> C -> D
               \         \
staging:        E -> F -> M  <-- (merge commit brings in hotfix)
```

**Use backport when:**
- ✅ After merging a hotfix PR to main
- ✅ Staging is behind main (check with `/git status`)
- ✅ Production deploy PR was merged and staging needs the changes

**Do NOT use for:**
- ❌ Syncing feature branches (use `/git sync` instead)
- ❌ Deploying staging to main (use `/git deploy` instead)

## Steps

1. **Check current branch**
   ```bash
   git branch --show-current
   ```

   **If not on staging:**
   ```
   You're on branch: feature/shopping-list

   Backport requires switching to staging. Continue? (yes / abort)
   ```

2. **Check for uncommitted changes**
   ```bash
   git status
   ```

   **If uncommitted changes exist:**
   ```
   You have uncommitted changes. Options:
   1. Stash changes and continue
   2. Abort and commit first
   ```

3. **Fetch and check if backport needed**
   ```bash
   git fetch origin
   git rev-list --count origin/staging..origin/main
   git log --oneline origin/staging..origin/main
   ```

   **If already up-to-date:**
   ```
   Staging is already up-to-date with main

   Commits in main: abc1234
   Commits in staging: abc1234

   No backport needed.
   ```

4. **Show backport preview**
   ```
   Backport Preview

   Commits to backport from main: 3

   - d4e5f6g Merge pull request #42 from hotfix/auth-leak
   - a1b2c3d fix(auth): prevent token leak in error responses
   - 9f8e7d6 Merge pull request #35 from staging

   Strategy: Merge main into staging (preserves history)

   Continue with backport? (yes / abort)
   ```

5. **Perform the backport**
   ```bash
   git checkout staging
   git pull origin staging
   git merge origin/main -m "chore: backport hotfixes from main

   Includes:
   - fix(auth): prevent token leak in error responses

   Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>"
   ```

   > **Why merge instead of rebase?** Staging is a shared branch. Merging preserves
   > history and doesn't rewrite commits, making it safer for integration branches.

6. **Handle conflicts (if any)**

   **If conflicts occur:**
   ```
   Conflict detected during backport

   Conflicting files:
   - backend/app/services/auth.py

   Options:
   1. Help me resolve this conflict
   2. Abort backport and return to previous state
   ```

   **If option 1 selected:**
   - Show the conflicting sections
   - Suggest resolution (usually prefer main's version for hotfixes)
   - After resolution:
     ```bash
     git add <resolved-files>
     git commit
     ```

   **If option 2 selected:**
   ```bash
   git merge --abort
   ```

7. **Push to remote**
   ```bash
   git push origin staging
   ```

8. **Confirm success**
   ```
   Backport complete!

   Branch sync status:
   - main:    abc1234 (production)
   - staging: def5678 (now includes hotfixes)

   Staging is now in sync with main. Normal workflow can resume.

   Next steps:
   - Continue feature work: /git start <type> <description>
   - Check status: /git status
   ```

## Commit Message Format

The backport merge commit should:
- Use `chore:` type (this is maintenance, not a feature)
- Reference what's being backported
- Include co-author line

**Template:**
```
chore: backport hotfixes from main

Includes:
- <list of hotfix commits>

Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>
```

**Example:**
```
chore: backport hotfixes from main

Includes:
- fix(auth): prevent token leak in error responses
- fix(recipes): handle null ingredient quantities

Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>
```

## Error Handling

**Staging has diverged significantly:**
```
Warning: Staging has diverged from main

Commits only in staging: 5
Commits only in main: 3

This may cause conflicts. Options:
1. Continue with merge (resolve conflicts if needed)
2. Abort and investigate manually
```

**Push rejected:**
```
Failed to push staging to origin

Someone else may have pushed to staging. Options:
1. Pull and retry
2. Abort (local staging has the merge)
```

**Nothing to backport:**
```
Nothing to backport

Staging is already up-to-date with main.
Both branches are at: abc1234
```

## Quick Reference

```
Backport Flow:
  1. /git backport              # Start backport
  2. Review commits to merge    # Verify what's coming in
  3. Confirm merge              # Creates merge commit
  4. Push to origin             # Sync remote staging

Typical usage after hotfix:
  1. /git hotfix <description>  # Create hotfix branch
  2. Make fix, /git commit      # Commit the fix
  3. Create PR to main          # Deploy to production
  4. Merge PR                   # Auto-deploys
  5. /git backport              # Sync to staging
```
