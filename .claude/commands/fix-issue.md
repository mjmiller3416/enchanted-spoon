# Fix GitHub Issue Command

You are an expert at automatically fixing GitHub issues while following project architecture patterns.

## Command Format

```
/fix-issue <issue-number>
```

## Your Task

When this command is invoked:

### 1. Fetch Issue Details

Use `gh` CLI to get the full issue:

```bash
gh issue view <issue-number> --json title,body,labels,comments,assignees,state
```

If the issue doesn't exist or `gh` is not installed, provide clear error message.

### 2. Analyze Issue Type

Examine labels and content to categorize:

- **Frontend**: Labels contain `frontend`, `ui`, `design`, `Next.js`, `React`, or mentions UI components
- **Backend**: Labels contain `backend`, `api`, `database`, `FastAPI`, `SQLAlchemy`, or mentions API/DB
- **Full-Stack**: Has both frontend and backend labels, or requires changes in both layers
- **Other**: Documentation, configuration, CI/CD, etc.

### 3. Create Branch

Invoke the git skill to create a properly named branch:

```
/git start "Fix #<issue-number>: <short-description>"
```

This creates: `claude/issue-<number>-<YYYYMMDD>-<HHMM>`

### 4. Plan Implementation

Use TodoWrite to create a comprehensive task list:

```
- [ ] Analyze issue requirements and gather context
- [ ] Read affected files and understand current implementation
- [ ] [Frontend/Backend/Full-stack specific tasks]
- [ ] Implement the fix
- [ ] Update types and API contracts (if applicable)
- [ ] Test the changes
- [ ] Run build/lint verification
- [ ] Document changes and next steps
```

Mark each task as you complete it.

### 5. Implement the Fix

**For Frontend Issues**:
1. Review the frontend-designer agent context (`.claude/agents/frontend-designer.md`)
2. Follow design system patterns (shadcn/ui, semantic tokens, proper components)
3. Read existing components to understand patterns
4. Make minimal, focused changes
5. Update TypeScript types if needed
6. Update API hooks in `hooks/api/` if needed
7. Ensure responsive design

**For Backend Issues**:
1. Review the backend-architect agent context (`.claude/agents/backend-architect.md`)
2. Follow layered architecture (DTOs → Services → Repositories → Models)
3. Read existing code to understand patterns
4. Create/update DTOs in `app/dtos/`
5. Implement business logic in Services
6. Add data access in Repositories
7. Update Models if schema changes
8. Create Alembic migration if database schema changed
9. Add/update tests in `tests/`

**For Full-Stack Issues**:
1. Implement backend first (API contract)
2. Test backend endpoints
3. Update frontend types to match backend DTOs
4. Implement frontend UI changes
5. Test end-to-end flow

**General Principles**:
- Always read files before modifying them
- Never create files unnecessarily - prefer editing existing files
- Follow existing code patterns and style
- Keep changes minimal and focused
- Don't over-engineer or add unnecessary features
- Use existing components and utilities
- Maintain type safety across the stack

### 6. Verification

Run appropriate verification based on what was changed:

**Frontend**:
```bash
cd frontend
npx tsc                    # Type checking
npm run lint               # Linting
npm run build              # Build verification (if major changes)
```

**Backend**:
```bash
cd backend
pytest tests/              # Run tests
# Check that dev server still runs
```

If tests fail, fix them before completing.

### 7. Provide Summary

After implementation, provide:

1. **Changes Made**:
   - List of files modified/created
   - Brief description of each change

2. **Testing Performed**:
   - What was tested
   - Test results

3. **Shipped**: ship through the normal git flow without waiting for review: `/git commit`, then
   `/git merge` (tests, squash into staging, fast-forward main). Report the shipped commit.

## Error Handling

### Issue Not Found
```
Error: Issue #<number> not found in this repository.

Please verify:
- The issue number is correct
- You have access to this repository
- The issue hasn't been deleted
```

### GitHub CLI Not Installed
```
Error: GitHub CLI (gh) is not installed or not authenticated.

Install:
- Windows: winget install GitHub.cli
- macOS: brew install gh
- Linux: See https://github.com/cli/cli#installation

Then authenticate: gh auth login
```

### Ambiguous Issue
If the issue is too vague or lacks details, use AskUserQuestion:

```
The issue description is quite general. To implement this correctly, I need clarification:

[Ask specific questions about requirements, scope, or implementation approach]
```

### Architectural Decisions Required
If the fix requires major architectural decisions:

```
This issue requires architectural decisions that should be discussed:

1. [Decision point 1]
2. [Decision point 2]

Please provide guidance on the preferred approach, or I can propose options for you to choose from.
```

## Integration with Other Skills

- **Git Skill** (`/git`): For branch creation, commit conventions
- **Frontend Designer Agent** (`frontend-designer`): For UI patterns and component scaffolding
- **Backend Architect Agent** (`backend-architect`): For API layered architecture patterns
- **Todo** (`/todo`): For creating GitHub issues if new issues are discovered

## Best Practices

1. **Read First**: Always read affected files before modifying
2. **Follow Patterns**: Match existing code style and architecture
3. **Minimal Changes**: Only change what's necessary for the fix
4. **Test Thoroughly**: Verify the fix works correctly
5. **Type Safety**: Maintain type safety across the stack
6. **Documentation**: Update comments/docs if behavior changes
7. **No Over-Engineering**: Prefer simple, direct solutions

## Example Workflows

### Example 1: Frontend Bug Fix - Issue #57

Issue: "Recipe card image not displaying on mobile"
Labels: `bug`, `frontend`, `ui`

```
1. Fetch issue: gh issue view 57
2. Create branch: /git start "Fix #57: Recipe card mobile image"
3. Analyze: Frontend UI bug
4. Read: components/recipe/RecipeCard.tsx
5. Fix: Update image responsive classes
6. Test: npm run lint, visual check on mobile
7. Summary: Changed aspect-ratio utilities in RecipeCard
```

### Example 2: Backend Feature - Issue #82

Issue: "Add recipe rating API endpoint"
Labels: `enhancement`, `backend`, `api`

```
1. Fetch issue: gh issue view 82
2. Create branch: /git start "Fix #82: Add rating API"
3. Analyze: Backend feature
4. Implement:
   - DTOs: RatingCreateDTO, RatingResponseDTO
   - Service: RatingService with business logic
   - Repository: RatingRepository with DB queries
   - Model: Rating model and relationships
   - Migration: Alembic migration for ratings table
   - Routes: POST /api/recipes/{id}/ratings
   - Tests: test_rating_service.py
5. Test: pytest tests/
6. Summary: Full rating API with CRUD operations
```

### Example 3: Full-Stack Feature - Issue #91

Issue: "Add favorite recipes feature"
Labels: `feature`, `frontend`, `backend`

```
1. Fetch issue: gh issue view 91
2. Create branch: /git start "Fix #91: Add favorites"
3. Analyze: Full-stack feature
4. Backend:
   - Model: user_favorite_recipes association
   - Repository: add_favorite(), remove_favorite()
   - Service: toggle_favorite() business logic
   - Route: POST /api/recipes/{id}/favorite
   - Migration: Alembic migration
5. Frontend:
   - Type: Update RecipeCardData with is_favorite
   - Hook: useFavoriteRecipe mutation
   - UI: Add heart icon to RecipeCard
   - Filter: Add favorites filter to FilterBar
6. Test: End-to-end flow
7. Summary: Full favorite feature with UI and API
```

## Constraints

- Maximum 15 todos in the task list
- Don't create documentation files unless explicitly required
- Ship through the normal git flow when done (`/git commit`, `/git merge`); no PR, no waiting for review
- Don't make destructive changes without confirmation

## Success Criteria

The fix is complete when:
1. ✅ Issue requirements are fully implemented
2. ✅ All verification steps pass (tests, lint, type check)
3. ✅ Code follows project architecture and style
4. ✅ Changes are minimal and focused
5. ✅ Types are updated and safe across stack
6. ✅ Ready for user review and commit

Now proceed with fixing issue #<issue-number>.