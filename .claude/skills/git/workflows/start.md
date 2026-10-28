# Workflow: start (`/git start <type> <description>`)

Valid types: `feature`, `fix`, `refactor`, `chore`, `docs`, `test`. Every task
gets a branch, however small.

1. **Validate.** Type from the list; description kebab-case, 2–4 words, `[a-z0-9-]`, no leading/trailing hyphen. If invalid, correct it yourself (closest type, shortened kebab-case description) and say what you used.
2. **Check the working tree.** `git status --short`. Uncommitted changes carry over to the new branch on their own. At commit time stage only what belongs to this task; leave anything else (another session's work, stray files) untouched.
3. **Create the branch from the latest staging.**
   ```
   git fetch origin
   git switch -c <type>/<description> origin/staging
   ```
   If the branch already exists: switch to it when it holds unmerged work for this same task, otherwise add `-2` to the name.
4. **Confirm.** Show the branch and base commit (`git log -1 --oneline origin/staging`). Next: build, `/git commit`, then `/git merge`.
