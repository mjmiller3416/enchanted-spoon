# Backend Architecture

**Layered architecture - strict separation of concerns.**

## Layer Responsibilities

| Layer | Responsibilities | CANNOT Do |
|-------|-----------------|-----------|
| **Routes** (`app/api/`) | HTTP handling, validation, error mapping, DI | Business logic, direct DB queries, import models for responses |
| **Services** (`app/services/`) | Business logic, transactions (COMMIT), multi-repo orchestration | Raise HTTPException, direct session queries |
| **Repositories** (`app/repositories/`) | Data access, queries, FLUSH only | COMMIT, business logic, raise domain exceptions |
| **Models** (`app/models/`) | Schema, relationships, constraints | Business logic, queries, validation |

## Dependency Flow (CRITICAL)

```
Routes → Services → Repositories → Models
   ↓        ↓            ↓
 DTOs     DTOs        Models
```

**Forbidden:**
- ❌ Routes → Repositories (skip service)
- ❌ Routes → Models directly (use DTOs)
- ❌ Services → Raw SQL (use repos)
- ❌ Repositories → commit() (services handle transactions)

## User Isolation (EVERY Model)

All domain models require `user_id` with `index=True`. All repositories filter by `user_id` in every query.

See models.md for model definition. See repositories.md for query filtering.

## Transaction Management

Services commit and rollback. Repositories only flush. See services.md for the standard transaction pattern.

## Error Handling

See exceptions.md for the complete exception hierarchy and HTTP status mapping.

## Existing Endpoints (Extend, Don't Duplicate)

| Domain | Base Route |
|--------|-----------|
| Recipes | `/api/recipes` |
| Meals | `/api/meals` |
| Planner | `/api/planner` |
| Shopping | `/api/shopping` |
| AI | `/api/ai/assistant` (+ other `/api/ai/*` feature routes) |

- ❌ Don't create `/api/recipes/search` when `/api/recipes?search=...` works
- ❌ Don't create `/api/favorites` when `/api/recipes?favorite=true` works
- ✅ Extend existing endpoints with query params

## Service Ownership

| Logic Type | Service |
|-----------|---------|
| Recipe-specific | `recipe_service.py` (flat) |
| Meal-specific | `services/meal/` (modular) |
| Planner-specific | `services/planner/` (modular) |
| Shopping-specific | `services/shopping/` (modular) |
| Data management | `services/data_management/` |
| Cross-domain | Create in owning service, call from others |

## Decision Tree: Where Does This Code Go?

| Question | YES → |
|----------|-------|
| HTTP-specific (status codes, headers)? | Route |
| Business rules or orchestration? | Service |
| Database CRUD? | Repository |
| Data transformation/validation? | DTO or Utility |

## Anti-Duplication Rule

Before creating new endpoints, services, repositories, or DTOs, search for existing ones. Extend with parameters instead of duplicating.

## New Feature Workflow

1. Model (`app/models/`) + Migration (`alembic revision --autogenerate`)
2. DTOs (`app/dtos/`) - Create, Update, Response, optionally Card
3. Repository (`app/repositories/`) - Takes `(session, user_id)`
4. Service (`app/services/`) - Takes `(session, user_id)`, commits transactions
5. Route (`app/api/`) - Uses `Depends(get_current_user)`, maps errors
6. Register in `main.py`

**See:** [app/services/recipe_service.py](../../backend/app/services/recipe_service.py) for complete reference implementation.
