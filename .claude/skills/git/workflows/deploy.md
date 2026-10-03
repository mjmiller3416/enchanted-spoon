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

3. **Write the release notes**

   Follow `.claude/commands/changelog.md` (the `/changelog` command) — it owns
   the editorial rules, the `RELEASES` format in
   `frontend/src/data/changelog.ts`, and the accept/edit/skip prompt.

   **Step 3a: Gather what ships**
   ```bash
   git log origin/main..origin/staging --pretty=format:"%s%n%b" --no-merges
   ```

   **Step 3b: Draft one release object** (headline, 1–3 highlights,
   improvements, fixes) for today's date, applying the filter rules —
   internal, security, integration and admin-only changes stay out.

   **Step 3c: Show preview and confirm** (`yes / edit / skip`)

   - If 'skip': Don't update the release notes this deploy

   **Step 3d: Commit and push**
   ```bash
   git add frontend/src/data/changelog.ts frontend/public/whats-new
   git commit -m "docs: update release notes for YYYY-MM-DD release

   Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>"
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
   - docs: update release notes for YYYY-MM-DD release

   ### Checklist
   - [ ] Tested on staging
   - [ ] No console errors
   - [ ] Verified on mobile
   - [ ] Release notes updated

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