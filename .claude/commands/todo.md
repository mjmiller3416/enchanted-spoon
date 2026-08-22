# TODO — GitHub Issue Generator

Create a GitHub issue from a problem description with auto-detected labels.

## Arguments

$ARGUMENTS

## Argument Format

```
/todo <description>                              → auto-detect type + priority
/todo [bug] [high] <description>                 → explicit labels (skip auto-detect)
/todo [enhancement] [low] add dark mode toggle   → partial override allowed
```

**Recognized bracket labels** (case-insensitive):
- **Type**: `[bug]`, `[enhancement]`, `[feedback]`, `[question]`, `[documentation]`
- **Priority**: `[high]`, `[medium]`, `[low]`, `[none]`

When both a type and priority bracket are provided, skip auto-detection entirely.
When only one category is provided, auto-detect the other.

---

## Instructions

### Step 1: Parse Arguments

1. Extract all `[bracket]` tokens from `$ARGUMENTS` (case-insensitive)
2. Map each token to a GitHub label:
   - `[bug]` → `bug`
   - `[enhancement]` → `enhancement`
   - `[feedback]` → `feedback`
   - `[question]` → `question`
   - `[documentation]` → `documentation`
   - `[high]` → `priority: high`
   - `[medium]` → `priority: medium`
   - `[low]` → `priority: low`
   - `[none]` → `priority: none`
3. Remove the bracket tokens from the arguments — the remaining text is the **problem description**
4. Track which categories were explicitly provided:
   - `hasExplicitType` = true if any type bracket was found
   - `hasExplicitPriority` = true if any priority bracket was found

If `$ARGUMENTS` is empty or missing, ask the user to describe the issue.

### Step 2: Search the Codebase

Use Grep and Glob to identify the most relevant file(s) related to the problem description. Look for:
- Component names, hook names, or service names mentioned in the description
- Related functionality keywords
- File patterns that match the feature area (e.g., `meal-planner`, `shopping-list`, `recipes`)

Record the primary file path and any secondary files for the issue body.

### Step 3: Auto-Detect Labels

For any label category **not** explicitly provided via brackets, apply these protocols:

#### Type Detection Protocol

Analyze the problem description and codebase search results. Assign the **first matching** type:

| Label           | Trigger Patterns                                                                                           |
|-----------------|------------------------------------------------------------------------------------------------------------|
| `bug`           | fix, broken, not working, error, fails, crash, regression, incorrect, wrong, reverts, disappears, 401, 403, auth failure, undefined, null, missing, doesn't, can't, won't, should but |
| `enhancement`   | add, implement, create, new, improve, support, enable, allow, extend, integrate, expose, combine, auto-populate, optimize, refactor, redesign, upgrade |
| `documentation` | document, docs, readme, guide, jsdoc, comments, explain, instructions, reference                           |
| `question`      | how to, why does, what is, is it possible, can we, should we, does it, where is                            |
| `feedback`      | user reported, feedback, user request, from user, customer, suggestion from                                |

If no pattern matches, default to `enhancement`.

#### Priority Detection Protocol

Analyze the problem description, the type label, and the affected files. Assign priority by severity:

| Label              | Criteria                                                                                                   |
|--------------------|------------------------------------------------------------------------------------------------------------|
| `priority: high`   | Core functionality broken, auth/security issues, data loss risk, blocking other features, production errors, API failures, CRUD operations broken |
| `priority: medium` | UX problems, non-blocking functional bugs, performance issues, important improvements, visible inconsistencies, incorrect data display |
| `priority: low`    | Polish, nice-to-haves, future enhancements, cosmetic issues, code cleanup, developer experience improvements |
| `priority: none`   | Questions, documentation-only tasks, feedback items with no clear immediate action                         |

**Priority heuristics based on type:**
- `bug` → default to `priority: medium` unless description indicates severity
- `enhancement` → default to `priority: low` unless description indicates importance
- `documentation` → default to `priority: none`
- `question` → default to `priority: none`
- `feedback` → default to `priority: none`

### Step 4: Create the GitHub Issue

#### Generate the Issue Title

- Start with a verb: Add, Fix, Enable, Prevent, Implement, Update, Expose, Combine, Remove
- Keep concise: 5–10 words max
- Make it scannable and specific
- Match the convention of existing issues in the repo

#### Generate the Issue Body

Use this template:

```markdown
## Description
[1-3 sentence summary of the problem or feature request from the user's perspective. Use em-dashes (—) instead of double hyphens.]

## Location
- `path/to/primary-file.tsx`
- `path/to/secondary-file.ts` (if applicable)

## Proposed Solution
[Concrete approach to fix or implement. Reference specific code patterns, hooks, components, or backend layers when applicable. Keep to 2-4 sentences.]
```

#### Create the Issue

Run this command using the Bash tool:

```bash
gh issue create \
  --title "<generated title>" \
  --label "<label1>,<label2>" \
  --body "<generated body>"
```

Use a HEREDOC for the body to preserve formatting:

```bash
gh issue create --title "Fix the login button auth failure" --label "bug,priority: high" --body "$(cat <<'EOF'
## Description
[body content here]

## Location
- `src/path/to/file.tsx`

## Proposed Solution
[solution here]
EOF
)"
```

#### Confirm the Result

Output this confirmation:

```
✅ Created GitHub Issue #XX: [Title]
   Labels: [label1], [label2]
   URL: https://github.com/mjmiller3416/enchanted-spoon/issues/XX
```

---

## Important Notes

- Always search the codebase first to provide accurate file locations
- If multiple files are relevant, list the primary file first and include others under Location
- If you can't find a relevant file, use your best judgment based on the description and project structure
- The `gh` CLI must be authenticated — if it fails, tell the user to run `gh auth login`
- Keep issue descriptions concise — the goal is quick capture, not detailed specs
- When auto-detecting, lean toward `bug` if the description implies something is broken, and `enhancement` if it implies something new or improved