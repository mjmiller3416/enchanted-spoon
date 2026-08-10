# Whiskful Backend Documentation

Reference for architecture decisions, patterns, and workflows. For API details, see FastAPI docs at `/docs`. For model/DTO fields, read the source files directly.

## Architecture Overview

```
Routes (app/api/) → Services (app/services/) → Repositories (app/repositories/) → Models (app/models/)
```

**Key principle:** Every route injects `current_user` via FastAPI dependency. Services and repos receive `(session, user_id)` to enforce tenant isolation. All domain models have a `user_id` foreign key.

```python
# Standard route pattern
@router.get("/things")
def list_things(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    service = ThingService(session, current_user.id)
    return service.list_all()
```

## Directory Structure

```
backend/app/
├── main.py                 # FastAPI app initialization, CORS, health endpoints
├── router.py               # Centralized route registration (24 routers)
├── api/                    # Route handlers (17 files + 7 in ai/)
│   ├── ai/                 # AI endpoints (assistant, recipe generation, recipe import, image gen, tips, suggestions, nutrition)
│   └── auth/               # Auth dependencies (get_current_user, require_pro, require_admin) + JWKS
├── services/               # Business logic layer
│   ├── ai/                 # AI services (Gemini client, assistant/, recipe_generation/, recipe_import/, image_generation/, etc.)
│   ├── meal/               # Modular: Core + SideRecipeMixin + QueryMixin
│   ├── planner/            # Modular: Core + EntryMgmt + StatusMgmt + BatchOps
│   ├── shopping/           # Modular: Core + ItemMgmt + Aggregation + Sync
│   ├── data_management/    # Modular: Core + Import + Export + Backup + Restore
│   └── *.py                # Flat services (recipe, ingredient, user, admin, github_service, etc.)
├── repositories/           # Data access layer (17 files, including planner/ and shopping/ sub-packages)
├── models/                 # SQLAlchemy ORM models (17 files)
├── dtos/                   # Pydantic validation models (21 files, including AI DTOs)
├── core/auth_config.py     # Clerk auth settings (JWKS URL derivation, dev mode bypass)
├── utils/                  # Unit conversion, dimension detection
└── database/               # DB connection, session management, Alembic migrations (32+ revisions)
```

## Authentication & Multi-Tenancy

### Auth Flow

Uses Clerk JWT (RS256). The JWKS URL is auto-derived from the publishable key (base64 decode → Clerk frontend API → `/.well-known/jwks.json`).

```
Bearer Token → get_current_user dependency
    ├─ AUTH_DISABLED=true? → return dev user (DEV_USER_ID)
    ├─ Fetch & cache JWKS (1hr TTL)
    ├─ Decode JWT, extract claims (sub, email, name, picture)
    └─ get_or_create_from_clerk() → User
```

### Account Claiming

Pre-provisioned users (family members not yet signed up) have `clerk_id = "pending_claim"`. When they sign in with a matching email, `get_or_create_from_clerk()` claims the account and links it to their real Clerk identity. This preserves any data you've set up for them.

### Subscription Access

`User.has_pro_access` checks three paths:
1. `is_admin = True` — permanent bypass
2. `subscription_tier = "pro"` + `subscription_status = "active"`
3. `granted_pro_until > now()` — temporary access for testers

Use `require_pro` dependency to gate pro-only endpoints.

## Key Patterns

### Diff-Based Shopping Sync

Shopping list items aren't regenerated from scratch—they use **diff-based sync** to preserve user edits (checked status, manual additions).

How it works:
- `ShoppingItemContribution` tracks which planner entries contribute to each item
- `aggregation_key` format: `"ingredient_name::dimension"` (e.g., `"butter::mass"`)
- When planner changes, system compares desired vs actual state and applies minimal updates
- Recipe sources are computed from contributions, not stored as a field

Why: If you check off "chicken" and then add another meal with chicken, the checked status persists while the quantity updates.

### Shopping Modes

Planner entries have a `shopping_mode` enum:
- `all` — all ingredients contribute to shopping list
- `produce_only` — only produce ingredients contribute
- `none` — excluded from shopping list (eating out, leftovers)

### Unit Conversion

`app/utils/unit_conversion.py` handles dimension detection (mass/volume/count) for ingredient aggregation. Custom per-ingredient rules stored in `UnitConversionRule` model.

### Soft Delete for Planner

`PlannerEntry.is_cleared` is a soft-delete that hides entries from the active view but preserves cooking history for streak calculation.

## AI Features

All AI features use Google Gemini (`google-genai>=1.0.0`). Services live in `app/services/ai/`, endpoints in `app/api/ai/`. Each AI feature uses a separate Gemini API key for independent rate limiting.

**Genie Assistant** (`services/ai/assistant/`):
- Multi-turn conversational AI with function calling
- Sub-package: `service.py`, `prompts.py`, `tools.py`, `context.py`, `generators.py`
- Uses `user_context_builder.py` to inject user's recipes, meals, planner state, shopping list
- Returns type-tagged responses: `{"type": "chat|suggestions|recipe|error", "response": ...}`

**Recipe Generation** (`services/ai/recipe_generation/`):
- Async operation with schema-driven JSON validation
- Input: prompt, preferences (diet, servings, cook_time), feature flags (estimate_nutrition, generate_image)
- Pro-only feature (`@require_pro` decorator)
- Mounted at `/api/ai/wizard-generation` (URL prefix predates the feature's current name — rename pending a frontend change, see `router.py`)

**Recipe Import** (`services/ai/recipe_import/`):
- Imports a recipe from an arbitrary URL — fetches the page, has Gemini extract structured recipe data
- Pro-only feature; endpoint at `/api/ai/recipe-import`

**Image Generation** (`services/ai/image_generation/`):
- Generates dual images (reference square + ultrawide banner) via Gemini Vision
- Pro-only feature. Full detail (Cloudinary keying, transformation pipeline, entry points): [`RECIPE_IMAGE.md`](RECIPE_IMAGE.md)

**Cooking Tips** (`services/ai/cooking_tips.py`): Context-aware cooking advice.

**Meal Suggestions** (`services/ai/meal_suggestions.py`): AI meal recommendations based on user data.

**Nutrition Estimation** (`services/ai/nutrition_estimation.py`): AI-inferred nutrition facts for recipes.

**Shared AI Utilities:**
- `gemini_client.py` - Lazy-initialized client factory with API key caching
- `config.py` - Model names and environment variable defaults
- `parse_utils.py`, `response_utils.py`, `text_utils.py` - Response processing

**Usage Tracking**: `UsageService` tracks AI calls per user in `UserUsage` model.

## Adding a New Feature

1. **Model** (`app/models/new_feature.py`)
   ```python
   class NewFeature(Base):
       __tablename__ = "new_features"
       id: Mapped[int] = mapped_column(primary_key=True)
       name: Mapped[str] = mapped_column(String(255))
       user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
   ```

2. **DTOs** (`app/dtos/new_feature_dtos.py`) — Pydantic models for create/update/response

3. **Repository** (`app/repositories/new_feature_repo.py`) — takes `(session, user_id)`

4. **Service** (`app/services/new_feature_service.py`) — takes `(session, user_id)`, instantiates repo

5. **Routes** (`app/api/new_feature.py`) — uses `Depends(get_current_user)`

6. **Register** in `app/router.py`: add router to the centralized `register_routes(app)` function

7. **Migration**: `alembic revision --autogenerate -m "add new_features table"`

## Migrations

```bash
alembic revision --autogenerate -m "description"  # Generate from model changes
alembic upgrade head                               # Apply pending
alembic downgrade -1                               # Rollback one
```

Always include `user_id` FK with `ondelete="CASCADE"` and `index=True` on new domain models.

## Constraints & Limits

| Feature | Limit | Why |
|---------|-------|-----|
| Planner entries | 15 max | UI/UX—weekly planning scope |
| Side recipes per meal | 3 max | Practical meal composition |
| Meal tags | 20 max, 50 chars each | Performance |
| Pagination | 100 items max | Response size |

## Environment Variables

See `.env.example` for full list. Key ones:

- `AUTH_DISABLED=true` — bypass auth for local dev
- `DEV_USER_ID` — user ID when auth disabled (default: 1)
- `CLERK_PUBLISHABLE_KEY` — used to derive JWKS URL
- `GEMINI_*_API_KEY` — separate keys for different AI features (rate limiting)

## Models Overview (17 files)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| User | Clerk-integrated user | clerk_id, email, is_admin, subscription_tier, `has_pro_access` property |
| Recipe | Full recipe | name, category, meal_type, prep_time, cook_time, `total_time` (hybrid property), images |
| RecipeIngredient | Recipe ↔ Ingredient junction | recipe_id, ingredient_id, quantity, unit |
| Ingredient | Global ingredient master | name, category, user_id (nullable for system) |
| NutritionFacts | Per-recipe nutrition | calories, protein_g, total_fat_g, carbs, fiber, etc. |
| RecipeHistory | Cooking history | recipe_id, cooked_at, notes |
| RecipeGroup | Recipe collections | name, user_id |
| Meal | Main + up to 3 sides | main_recipe_id, side1/2/3_id, is_saved |
| PlannerEntry | Meal in planner | meal_id, position, is_completed, is_cleared, shopping_mode |
| ShoppingItem | Shopping list item | ingredient_name, quantity, unit, aggregation_key, have, flagged |
| ShoppingItemContribution | Source tracking | shopping_item_id, planner_entry_id |
| UnitConversionRule | Unit conversion | from_unit, to_unit, conversion_factor |
| UserSettings | User preferences | Various preference fields |
| UserCategory | Custom recipe categories | name, user_id |
| UserIngredientCategory | Custom ingredient categories | name, user_id |
| UserIngredientUnit | Custom units | name, abbreviation, user_id |
| UserUsage | AI feature usage | feature, count, period |

## Gotchas

**SQLite foreign keys**: Enabled via `PRAGMA foreign_keys=ON` listener in `db.py`. If you're seeing FK violations not caught, check this is running.

**Cascade deletes**: All domain models cascade from User. Recipe → RecipeIngredient, Meal → PlannerEntry also cascade. Check `ondelete="CASCADE"` on FKs.

**Session management**: Routes get session via `Depends(get_session)`. Don't create sessions manually in services/repos—they receive it from the route.

**Timezone handling**: Streak calculation (`/api/planner/streak`) requires `tz` query param from client. Server stores UTC, client converts.

**AI API keys**: Using separate Gemini keys per feature allows independent rate limiting. All defined in env vars: `GEMINI_ASSISTANT_API_KEY`, `GEMINI_TIP_API_KEY`, `GEMINI_IMAGE_API_KEY`, `GEMINI_RECIPE_GENERATION_API_KEY`, `GEMINI_NUTRITION_API_KEY`.

**Recipe total_time**: Computed as a SQLAlchemy hybrid property (prep_time + cook_time), not stored in the database. Dropped the column in migration `20260617_drop_total_time_column`.