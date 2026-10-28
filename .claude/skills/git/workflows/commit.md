# Workflow: commit (`/git commit [message]`)

1. **Look at the changes.**
   ```
   git status --short
   git diff --stat
   git diff --cached --stat
   ```
   Nothing to commit → say so and stop.

2. **Check the branch.**
   - **On `main` or `staging`:** don't commit there. Move the work onto a branch first: `git switch -c <type>/<description>` (uncommitted changes come along), then continue.
   - **On a typed branch:** commit here. If the changes clearly belong to a different area than the branch name, commit anyway and mention it in the summary.

3. **Pick what to stage.** Specific paths over `git add -A`: the files this task changed. Never stage `.env` or anything under `.venv/`, `node_modules/` or `.next/`. Leave unrelated changes unstaged without asking.

4. **Message.** Use the provided message or write one from the diff, then validate:
   - `<type>(<scope>): <description>`; type in `feat fix chore refactor docs test style perf`
   - lowercase type, scope and first word; imperative mood; no trailing period; ≤ 72 chars
   - optional body after a blank line for the why
   Invalid → fix it yourself.

5. **Commit.**
   ```
   git add <paths>
   git commit -m "<subject>" -m "<optional body>" -m "Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>"
   ```

6. **Confirm.** Show the short hash, subject and files changed. Next: `/git merge` (it runs the tests, merges and deploys).
