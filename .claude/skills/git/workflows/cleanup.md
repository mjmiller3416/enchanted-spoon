# Workflow: cleanup (`/git cleanup`)

Delete branches whose work is already in `staging`, locally and on GitHub.
Works with squash merges. Merged branches go without asking; unmerged ones
are only reported.

1. **Refresh.**
   ```
   git fetch origin --prune
   git branch --format="%(refname:short)"
   git branch -r --format="%(refname:short)"
   ```
   Never touch `main`, `staging` or `HEAD`. If you're on a branch that will be deleted, `git switch staging` first.

2. **Classify each branch** (local and remote-only), using the trial-merge check from SKILL.md:
   ```
   git merge-tree --write-tree origin/staging <branch>
   git rev-parse "origin/staging^{tree}"
   ```
   Old `hotfix/*` branches are checked against `origin/main` instead.
   - **Merged:** trees match → delete.
   - **Unmerged:** trees differ → keep. Report its last commit date (`git log -1 --format=%cr <branch>`) and flag anything older than 30 days as stale.
   - **Conflicted:** merge-tree exits non-zero → keep and report. Most often the branch *was* squash-merged and staging edited the same lines afterwards. If `git log --oneline --grep "Squashed from <branch>" origin/staging` finds the squash commit, delete it; otherwise treat it as real unmerged work.

3. **Delete merged branches.**
   ```
   git branch -D <branch>
   git push origin --delete <branch>
   ```
   One command per branch; a failure on one doesn't stop the rest.

4. **Close resolved issues (needs gh).** For deleted branches named `.../issue-<N>-...`, and for `Closes/Fixes/Resolves #N` in `git log origin/staging origin/main -n 100 --format=%B`, close the still-open ones (`gh issue view <N> --json state,title`):
   ```
   gh issue close <N> --comment "Resolved by <branch> (merged to staging). Closed via /git cleanup."
   ```
   Never close issues tied only to unmerged or stale branches.

5. **Summary:** a table of deleted and kept branches (with reasons), and issues closed.
