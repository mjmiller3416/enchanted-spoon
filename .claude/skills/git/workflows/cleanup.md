# Workflow: `cleanup`

**Usage:** `/git cleanup`

Removes local and remote branches that have already been merged, then closes the
GitHub issues those merged branches resolved. Feature branches merged to staging
and hotfix branches merged to main are both cleaned up.

> **Why close issues here?** In this solo workflow, feature branches squash-merge
> **directly to `staging`** (no PR, and `staging` is not the default branch).
> GitHub only auto-closes issues from `Closes #N` / `Fixes #N` keywords when the
> commit lands on the **default branch** via a merged PR — which never happens for
> feature work here. So issues fixed via `/fix-issue` stay open forever unless
> closed manually. Cleanup sweeps them alongside their branches.

## When to Use

- After accumulating stale branches over several features
- Periodic maintenance to keep your branch list tidy
- After a deploy cycle (features merged to staging, staging merged to main)
- To close resolved issues left open because feature merges bypass the default branch

## Requirements

- `git` (always required)
- `gh` (GitHub CLI, authenticated) — required only for the **issue cleanup** phase.
  If `gh` is missing or unauthenticated, branch cleanup still runs; issue cleanup
  is skipped with a notice.

---

# Part 1 — Branch Cleanup

## Steps

1. **Fetch and prune remote tracking refs**
   ```bash
   git fetch origin --prune
   ```

   > **Why prune?** This removes local tracking references to remote branches that
   > no longer exist on origin (e.g., deleted after a PR merge).

2. **Identify branches to clean up**

   Scan for branches in three categories:

   **A. Local branches merged to staging:**
   ```bash
   git branch --merged origin/staging
   ```
   Filter out `main` and `staging` (protected branches).

   **B. Local branches merged to main** (hotfix branches):
   ```bash
   git branch --merged origin/main
   ```
   Filter out `main` and `staging`.

   **C. Stale remote-tracking branches** (remote already deleted):
   ```bash
   git branch -vv | grep ': gone]'
   ```

   Deduplicate across all three categories.

   > **Track which branch was merged vs. stale.** You'll need this in Part 2:
   > issues behind **merged** branches (A/B) are safe to close; issues behind
   > **stale-only** branches (C) may be abandoned work and are NOT closed by default.

3. **Show cleanup preview**
   ```
   Branch Cleanup Preview

   Merged to staging (safe to delete):
     - feature/shopping-sync         (local + remote)
     - fix/issue-142-token-refresh   (local only)
     - chore/update-deps             (local + remote)

   Merged to main (hotfix branches):
     - hotfix/auth-token-leak        (local + remote)

   Stale (remote already deleted):
     - refactor/api-client           (local only, remote gone)

   Protected (will NOT be deleted):
     - main
     - staging

   Total: 5 branches to remove

   Proceed with cleanup? (yes / abort)
   ```

   **If no branches to clean:**
   ```
   No stale branches found

   All branches are either active or protected. Nothing to clean up.
   ```

   > Even when there are no branches to clean, still run Part 2 — issues from
   > previously-deleted branches may remain open.

4. **Delete local branches**

   Use safe delete (`-d`) for merged branches first:
   ```bash
   git branch -d feature/shopping-sync fix/issue-142-token-refresh chore/update-deps hotfix/auth-token-leak
   ```

   For stale branches where the remote is already gone, use force delete (`-D`)
   since git can't verify the merge status against a deleted remote:
   ```bash
   git branch -D refactor/api-client
   ```

   > **Safety:** `-d` (lowercase) refuses to delete unmerged branches.
   > `-D` (uppercase) is only used for branches whose remote is already gone,
   > meaning the work was already merged or intentionally abandoned on the remote.

5. **Delete remote branches**

   Only delete remotes that still exist on origin:
   ```bash
   git push origin --delete feature/shopping-sync chore/update-deps hotfix/auth-token-leak
   ```

   > **Note:** Skip branches whose remote was already pruned in step 1.

6. **Confirm branch cleanup**
   ```
   Branch cleanup complete!

   Deleted 5 branches:
     Local:  5 removed
     Remote: 3 removed (2 were already gone)

   Remaining branches:
     - main (protected)
     - staging (protected)
     - feature/new-dashboard (active, not merged)
   ```

---

# Part 2 — GitHub Issue Cleanup

Runs after branch cleanup. Closes issues whose fix has already merged.

## Steps

1. **Check `gh` availability**
   ```bash
   gh auth status
   ```

   **If `gh` is missing or not authenticated:**
   ```
   Skipping issue cleanup — GitHub CLI (gh) is not installed or authenticated.

   Branch cleanup finished. To also close resolved issues, install and
   authenticate gh, then re-run /git cleanup:
     gh auth login
   ```
   Stop here (branch cleanup already succeeded).

2. **Collect candidate issue numbers**

   Gather from two signals, tagging each candidate with a confidence level.

   **A. From merged branch names** (high confidence).
   The `/fix-issue` command names branches `.../issue-<N>-...`. For every branch
   deleted in Part 1 that was **merged** (categories A/B, not stale-only), extract
   the issue number:
   ```bash
   # Example: derive issue numbers from the merged-branch list you built in Part 1
   printf '%s\n' "${MERGED_BRANCHES[@]}" | grep -oiE 'issue-[0-9]+' | grep -oE '[0-9]+' | sort -u
   ```

   **B. From staging/main commit messages** (high confidence).
   Squash-merge commits carry `Squashed from: <branch>` and may include closing
   keywords. Scan recent history on the integration branches for references:
   ```bash
   git log origin/staging origin/main --format='%s%n%b' -n 100 \
     | grep -oiE '(close[sd]?|fix(e[sd])?|resolve[sd]?)[[:space:]]+#[0-9]+' \
     | grep -oE '[0-9]+' | sort -u
   ```
   Also fold in any `issue-<N>` strings from the same log range (they appear via
   the `Squashed from:` trailer).

   **C. From stale-only branch names** (low confidence — verify manually).
   Extract `issue-<N>` numbers from branches that were only in the stale category
   (remote gone, force-deleted). These may be **abandoned**, not merged — list them
   but do NOT close by default.

   Deduplicate. A number appearing in both A/B and C is treated as high confidence.

3. **Cross-check against open issues**

   Only issues that are currently **open** can be closed. Fetch open issues and
   keep only candidates that are actually open (drop already-closed / nonexistent
   numbers silently):
   ```bash
   gh issue list --state open --limit 200 --json number,title
   ```
   For each surviving candidate, pull its title for the preview:
   ```bash
   gh issue view <N> --json number,title,state
   ```

4. **Show issue cleanup preview**
   ```
   Issue Cleanup Preview

   Resolved (fix merged — will close):
     - #142  Recipe card image not displaying on mobile   (fix/issue-142-token-refresh → staging)
     - #150  Add recipe rating endpoint                    (Closes #150 on staging)

   Uncertain (from abandoned/stale branch — will NOT close):
     - #131  Refactor api client                           (refactor/api-client, remote gone)

   Already closed / not found (skipped):
     - #128, #99

   Total: 2 issues to close

   Close resolved issues? (yes / choose / abort)
   ```

   - `yes` → close everything under **Resolved**.
   - `choose` → let the user pick a subset (and optionally include Uncertain ones).
   - `abort` → skip issue closing (branch cleanup is already done).

   **If no candidates:**
   ```
   No resolved issues to close.
   ```

5. **Close the confirmed issues**

   Close each with a comment linking it to the merge, so the trail is auditable:
   ```bash
   gh issue close <N> --comment "Resolved by <branch> (merged to staging). Closed via /git cleanup."
   ```

   > **Never reopen or edit** issue bodies here — only close, only with a comment.
   > Never close an **Uncertain** issue unless the user explicitly opted in via
   > `choose`.

6. **Confirm success**
   ```
   Cleanup complete!

   Branches:
     Local:  5 removed
     Remote: 3 removed (2 were already gone)

   Issues:
     Closed: 2  (#142, #150)
     Skipped: 1 uncertain (#131), 2 already closed

   Remaining branches:
     - main (protected)
     - staging (protected)
     - feature/new-dashboard (active, not merged)

   Tip: Run /git cleanup periodically to keep branches and issues tidy.
   ```

## Error Handling (Issues)

**`gh` not authenticated:** Skip Part 2 with the notice in step 1. Branch cleanup
already succeeded — never fail the whole command over issue cleanup.

**Issue close fails (permissions / network):**
```
Warning: Could not close issue #142

The issue may lack permissions, be already closed, or the network failed.
Skipping. Close manually: gh issue close 142
```
Continue with the remaining issues.

**Candidate maps to a closed or deleted issue:** Skip silently (listed under
"Already closed / not found").

---

## Error Handling (Branches)

**Currently on a branch that would be deleted:**
```
You're currently on branch: feature/shopping-sync

This branch is merged and would be deleted. Switching to staging first.
```

Then:
```bash
git checkout staging
git pull origin staging
```

**Delete fails for a branch:**
```
Warning: Could not delete branch 'feature/shopping-sync'

This may mean it has unmerged commits. Skipping.
To force delete: git branch -D feature/shopping-sync
```

**Remote delete fails:**
```
Warning: Could not delete remote branch 'feature/shopping-sync'

The remote branch may have already been deleted or you lack permissions.
Skipping remote deletion for this branch.
```

**Uncommitted changes on current branch:**
```
You have uncommitted changes on your current branch.

Options:
1. Stash changes and continue cleanup
2. Abort and commit first
```

## Protected Branches

The following branches are **never deleted**, regardless of merge status:

- `main` — production branch
- `staging` — integration branch

## Quick Reference

```
Cleanup Flow:
  1. /git cleanup                # Start cleanup
  2. Review branch list          # Verify what will be deleted
  3. Confirm deletion            # Removes local + remote branches
  4. Review issue list           # Verify which issues will close
  5. Confirm issue closing       # Closes resolved issues with a comment
  6. Done                        # Protected branches remain

What gets cleaned:
  Branches
    - feature/*, fix/*, chore/*, refactor/*, docs/*, test/* merged to staging
    - hotfix/* merged to main
    - Any branch whose remote tracking ref is gone
  Issues
    - Open issues whose fix branch (issue-<N>) merged to staging/main
    - Open issues referenced by Closes/Fixes/Resolves #N on staging/main
    - Abandoned/stale-branch issues are listed but NOT auto-closed
```
