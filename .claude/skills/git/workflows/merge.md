# Workflow: `merge`

**Usage:** `/git merge`

Merges your current feature branch directly into staging. This is the **primary way to integrate completed features** in a solo workflow (no PR needed for feature -> staging).

## When to Use

- Feature is complete and ready for integration
- You've tested your changes locally
- You want fast iteration without PR overhead

## Steps

1. **Pre-flight checks**
   ```bash
   git status                         # Check for uncommitted changes
   git fetch origin
   git log origin/staging..HEAD       # Your commits to merge
   ```

   **If uncommitted changes:**
   ```
   You have uncommitted changes. Commit them first with `/git commit`
   ```

   **If no commits:**
   ```
   No commits on this branch. Nothing to merge.
   ```

2. **Check branch is synced**
   ```bash
   git rev-list --count HEAD..origin/staging
   ```

   **If behind staging:**
   ```
   Your branch is behind staging by 3 commits.

   You should sync first to avoid merge conflicts:
      /git sync

   Or continue anyway? (sync first / merge anyway)
   ```

3. **Show merge preview**
   ```
   Merge Preview

   Branch: feature/shopping-list -> staging
   Commits to merge: 4

   Commits:
   - abc1234 feat: add shopping list sync
   - def5678 feat: add list filtering
   - ghi9012 feat: add sort options
   - jkl3456 fix: resolve edge case

   Merge strategy: Squash merge (single commit on staging)

   Proceed? (yes / abort)
   ```

4. **Perform the merge**
   ```bash
   git checkout staging
   git pull origin staging
   git merge --squash feature/shopping-list
   git commit -m "feat: shopping list sync and filtering

   - Add real-time sync for shopping list items
   - Add list filtering and sorting
   - Fix edge case in item removal

   Squashed from: feature/shopping-list (4 commits)
   Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>"
   ```

   > **Why squash merge?** It keeps staging history clean -- one commit per feature
   > instead of all your WIP commits. The detailed history lives in git reflog
   > if you ever need it.

5. **Push merge to remote**

   After a successful merge, immediately push staging to origin:
   ```bash
   git push origin staging
   ```

   **If push fails:**
   ```
   Failed to push staging to origin.

   Options:
   1. Pull and retry (may have new remote commits)
   2. Abort (your local staging has the merge -- push manually later)
   ```

6. **Delete feature branch**

   Once the merge is pushed, clean up the feature branch:
   ```bash
   git branch -d feature/shopping-list           # Delete local branch
   git push origin --delete feature/shopping-list # Delete remote branch (if pushed)
   ```

   > **Note:** `git branch -d` (lowercase) is a safe delete -- it only works
   > if the branch has been fully merged. This prevents accidental data loss.

7. **Confirm success**
   ```
   Merged to staging!

   Commit: xyz7890 feat: shopping list sync and filtering
   Pushed: origin/staging
   Branch: feature/shopping-list (deleted local + remote)

   Staging is now ready for testing.

   When ready for production: /git deploy
   ```

## Merge Commit Message

The squash merge commit message should:
- Summarize the feature (first line = PR title equivalent)
- List key changes as bullet points
- Reference the source branch
- Include co-author line

**Example commit message:**
```
feat: shopping list sync and filtering

- Add real-time sync for shopping list items
- Add list filtering by recipe source
- Add sort options (A-Z, category, recipe)
- Fix edge case in item quantity merging

Squashed from: feature/shopping-list (4 commits)
Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>
```

## Error Handling

**Branch has conflicts with staging:**
```
Merge conflict detected

Conflicting files:
- frontend/src/hooks/api/useShopping.ts

You need to resolve conflicts before merging.

Options:
1. Sync branch first (/git sync) then retry merge
2. Manually resolve and continue
3. Abort merge
```

**Failed to delete branch:**
```
Warning: Could not delete remote branch

The merge succeeded but remote branch deletion failed.
You can manually delete it later:
   git push origin --delete feature/shopping-list
```

## Cleaning Up Old Branches

If you accumulate stale branches over time:

```bash
# List branches that have been merged to staging
git branch --merged staging

# List branches that no longer exist on remote
git fetch --prune
git branch -vv | grep ': gone]'

# Delete local branches merged to staging (safe)
git branch --merged staging | grep -v "staging\|main" | xargs git branch -d

# Delete local branches tracking deleted remotes
git fetch --prune
git branch -vv | grep ': gone]' | awk '{print $1}' | xargs git branch -D
```

**Warning**: Only delete branches you're certain are merged. The `-d` flag prevents deletion of unmerged work.