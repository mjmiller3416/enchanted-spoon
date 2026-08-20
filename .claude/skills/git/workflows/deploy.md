# Workflow: `deploy`

**Usage:** `/git deploy`

Creates a PR from staging -> main to deploy to production. This is the **only place PRs are used** in the solo workflow.

## 🚨 NEVER click "Delete branch" after merging a deploy PR

The deploy PR is `staging -> main`, which makes **`staging` the PR's head branch**. GitHub's
post-merge "Delete branch" button deletes the *head* branch -- so clicking it deletes your
permanent integration branch, not a spent feature branch. The button means "tidy up" everywhere
else in the workflow and "destroy infrastructure" here.

This has happened: PR #185 was merged 2026-08-17 19:20:10 EDT and `refs/heads/staging` was deleted
6 seconds later. It stayed gone for two days.

**Guard rail:** repository ruleset `protect-staging-from-deletion` now blocks deletion of
`refs/heads/staging` (no bypass actors, so it applies to the repo owner too). The button should be
rejected if clicked. Do not disable the ruleset to "clean up" -- there is nothing to clean up.

**Symptom if `staging` is ever missing again:**
```
fatal: couldn't find remote ref staging
```
A stale local `origin/staging` will still resolve, because a plain `git fetch` does not prune --
so pre-flight checks look healthy and will mislead you. Confirm with `git ls-remote origin staging`
(authoritative) rather than `git log origin/staging` (cached), and check
`gh api repos/<owner>/<repo>/events` for a `DeleteEvent` to see when it happened.

**Recovery:** re-push `staging` from any local clone that still has it. No commits are lost -- a
merged branch's commits stay reachable from `main`, so deletion removes a pointer, not history.

## Why PR for Deploy?

Even solo, a PR for production deploys gives you:
- A checkpoint to review all changes going to production
- A clear record in GitHub of what was deployed when
- Easy rollback (revert the PR)
- CI checks run before deploy (if configured)

## Steps

1. **Pre-flight checks**

   > **Always use `origin/` refs** (e.g., `origin/main`, `origin/staging`) for all
   > comparisons. Never compare local `main` vs `staging` -- local refs may be stale
   > and will overstate the diff.

   ```bash
   git fetch origin
   git checkout staging
   git pull origin staging
   git log origin/main..origin/staging --oneline   # Commits to deploy
   git diff origin/main..origin/staging --stat      # Files changed
   ```

   **If staging equals main:**
   ```
   Nothing to deploy. Staging and main are in sync.
   ```

2. **Show deploy preview**
   ```
   Deploy Preview (staging -> main)

   Commits to deploy: 3

   - xyz7890 feat: shopping list sync and filtering
   - abc1234 feat: improved meal planner drag-drop
   - def5678 fix: resolve auth token refresh

   This will trigger Railway auto-deploy to production.

   Create deploy PR? (yes / abort)
   ```

3. **Auto-generate changelog entry**

   **Step 3a: Parse commits**
   ```bash
   git log origin/main..origin/staging --pretty=format:"%s" | grep -E "^(feat|fix):"
   ```

   **Step 3b: Categorize and convert to user-friendly language**

   Categorization rules:
   - `feat:` or `feat(*):`     → "New Features"
   - `fix:` (user-visible)     → "Bug Fixes"
   - `chore:`, `refactor:`, `docs:`, `test:` → SKIP (internal only)

   **Step 3c: Generate changelog markdown**

   Format matching existing style in `frontend/src/data/changelog.ts`:
   ```markdown
   ## YYYY-MM-DD - New Features
   - [User-friendly description with em dashes — for clarifications]

   ## YYYY-MM-DD - Bug Fixes
   - [User-friendly description]

   ## YYYY-MM-DD - Improvements
   - [User-friendly description for enhancements]
   ```

   **Conversion guidelines:**
   - Remove technical jargon (file names, function names, etc.)
   - Focus on user impact ("what changed" not "how")
   - Use proper em dashes (—) not hyphens for clarifications
   - Mention specific feature areas (Genie, Shopping List, Recipe Browser, Meal Planner, etc.)
   - Combine related commits into single bullets when appropriate
   - Use present tense and active voice
   - Start with action verbs when possible

   **Examples:**
   ```
   Commit: feat(planner): add drag and drop reordering
   Changelog: Drag-and-drop reordering of meals in the Meal Planner sidebar

   Commit: fix(shopping): resolve category collapse bug
   Changelog: Shopping list categories now auto-collapse when all items are collected

   Commit: feat: implement recipe search with filters
   Changelog: New multi-select filters in Recipe Browser for easier recipe searching

   Commit: fix(auth): prevent token leak in error responses
   Changelog: Fixed authentication issue with AI features — image generation and Genie now properly authenticate requests
   ```

   **Step 3d: Show preview and confirm**
   ```
   Generated changelog entry:

   ## 2026-01-31 - New Features
   - Shopping list sync and real-time updates across devices
   - New meal planning suggestions based on existing recipes

   ## 2026-01-31 - Bug Fixes
   - Fixed shopping list category collapse issue when all items collected
   - Resolved authentication issue with AI features

   Accept this changelog entry? (yes / edit / skip)
   ```

   - If 'edit': Open in editor, allow modifications
   - If 'skip': Don't update changelog this deploy
   - If 'yes': Continue to step 3e

   **Step 3e: Insert into changelog file**

   Read `frontend/src/data/changelog.ts`
   Insert new section at line 5 (after opening backtick, before first ##)
   Preserve all existing entries

   **Step 3f: Commit and push changelog**
   ```bash
   git add frontend/src/data/changelog.ts
   git commit -m "docs: update changelog for YYYY-MM-DD release

   Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
   git push origin staging
   ```

4. **Create the PR**
   ```bash
   gh pr create --base main --head staging --title "Deploy: <summary>" --body "..."
   ```

   PR body template:
   ```markdown
   ## Production Deploy

   ### Changes
   - feat: shopping list sync and filtering
   - feat: improved meal planner drag-drop
   - fix: resolve auth token refresh
   - docs: update changelog for YYYY-MM-DD release

   ### Checklist
   - [ ] Tested on staging
   - [ ] No console errors
   - [ ] Verified on mobile
   - [ ] Changelog updated

   ---
   Merging this PR will trigger Railway auto-deploy.
   ```

4. **Confirm**
   ```
   Deploy PR created!

   #42: Deploy: Shopping list sync, planner improvements
   https://github.com/user/repo/pull/42

   Next steps:
   1. Review the changes in GitHub
   2. Merge the PR when ready
   3. DO NOT click "Delete branch" on the merged PR -- that deletes `staging`
   4. Railway will auto-deploy to production
   ```

## Rolling Back a Deploy

If you need to revert a deployment:

**Option 1: Revert the merge commit on main**
```bash
git checkout main
git pull origin main
git revert <merge-commit-sha> -m 1
git push origin main
# Then backport revert to staging
git checkout staging
git cherry-pick <revert-commit-sha>
git push origin staging
```

**Option 2: Revert PR in GitHub**
- Go to the merged PR in GitHub
- Click "Revert" button
- GitHub creates a new PR with the revert
- Merge it to deploy the rollback
- Manually backport to staging

**Note:** For urgent production fixes, use the hotfix workflow (`/git hotfix`) instead of deploy + revert.