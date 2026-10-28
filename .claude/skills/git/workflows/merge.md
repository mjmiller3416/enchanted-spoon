# Workflow: merge (`/git merge`)

Squash-merge the current typed branch into `staging`, push it, deploy
(fast-forward `main` to `staging`) and delete the branch. No confirmation at
any step.

1. **Pre-flight.**
   ```
   git status --short
   git fetch origin
   git log --oneline origin/staging..HEAD
   ```
   Uncommitted changes from this task → `/git commit` first. No commits → nothing to merge; stop.
   On `main` or `staging` → move the work to a branch first (`workflows/commit.md` step 2).

2. **Behind staging?** `git rev-list --count HEAD..origin/staging` > 0 → run `/git sync` first, without asking.

3. **Tests.** For the areas touched: from `backend/`: `venv/Scripts/python -m pytest tests -q`; from `frontend/`: `npm run lint`, `npx tsc --noEmit` and `npm test`. A failure → fix it on the branch, commit, rerun. If you can't fix it, stop here: the work stays committed on the branch, report the failure. Never merge red.

4. **Release notes.** If the branch has user-facing changes, follow `.claude/commands/changelog.md` to write them up in `frontend/src/data/changelog.ts` (add to today's release if `RELEASES` already has one, otherwise prepend a new one) and commit on the branch: `docs: update release notes for YYYY-MM-DD release`. No accept/edit/skip prompt: put the release text in the summary. Internal, security, integration and admin-only changes get no entry; nothing user-facing → skip this step.

5. **Squash message.** The subject follows the branch type (`feature` → `feat`, `fix` → `fix`, `refactor` → `refactor`, others → `chore`/`docs`/`test`):
   ```
   feat: shopping list sync and filtering

   - add real-time sync for list items
   - add filtering and sort options

   Squashed from feature/shopping-sync (4 commits)

   Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>
   ```

6. **Merge.**
   ```
   git switch staging
   git pull --ff-only origin staging
   git merge --squash <branch>
   git commit -m "<subject>" -m "<body>"
   ```
   Conflicts during `merge --squash` → `git reset --merge`, `git switch <branch>`, `/git sync` (resolve there), rerun the tests, and come back to this step.

7. **Production-only commits?** Usually the merge commits of old deploy PRs.
   ```
   git rev-list --count staging..origin/main
   ```
   Anything but 0 → `git merge --no-edit origin/main`, so the push to `main` below is a fast-forward.

8. **Push staging.**
   ```
   git push origin staging
   ```
   Rejected (something landed meanwhile) → `git pull --rebase origin staging`, then push again.

9. **Deploy.** Follow `workflows/deploy.md` from step 2.

10. **Verify, then delete the branch.** `git branch -d` refuses after a squash merge (git can't see the ancestry), so prove the work is in staging first:
   ```
   git fetch origin
   git merge-tree --write-tree origin/staging <branch>
   git rev-parse "origin/staging^{tree}"
   ```
   First line of the first output == second output → the branch adds nothing that staging lacks. Then:
   ```
   git branch -D <branch>
   git push origin --delete <branch>
   ```
   (The remote delete fails harmlessly if the branch was never pushed.) If the trees differ, keep the branch and say so in the summary.

11. **Confirm.** The squash commit (hash + subject), now on `staging` and `main`, branch deleted, Railway deploying staging and production.
