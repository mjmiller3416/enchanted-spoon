# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Enchanted Spoon** is a full-stack recipe management and meal planning application with AI-powered features. It consists of:

- **Frontend**: Next.js 16 + React 19 with TypeScript, Tailwind CSS v4, shadcn/ui (New York style)
- **Backend**: FastAPI + SQLAlchemy 2.0 with Pydantic v2, SQLite (dev) / PostgreSQL (prod)
- **AI**: Google Gemini integration for recipe generation, cooking tips, meal suggestions, and image generation

---

## 🚨 CRITICAL RULES - ALWAYS ENFORCE 🚨

**These rules MUST be followed in EVERY edit, regardless of context window state or session length.**

### Frontend - Never Violate

| ❌ WRONG | ✅ CORRECT | Rule |
|---------|-----------|------|
| `text-gray-500`, `bg-slate-800` | `text-muted-foreground`, `bg-card` | Use semantic tokens only |
| `<div className="bg-card border">` | `<Card>` from `@/components/ui/card` | Use shadcn components |
| `h-[38px]`, `gap-[15px]` | `h-10`, `gap-4` | Use Tailwind scale (no arbitrary values) |
| `<Button size="icon"><X /></Button>` | `<Button size="icon" aria-label="Close">` | Icon buttons need aria-label |
| Icons from `react-icons` | Icons from `lucide-react` with `strokeWidth={1.5}` | Lucide React only |
| `<button onClick={...}>` | `<Button variant="..." onClick={...}>` | Use Button component |
| Missing loading states | `<Button disabled={loading}><Loader2 className="animate-spin" /></Button>` | Show loading spinner |

### Backend - Never Violate

| ❌ WRONG | ✅ CORRECT | Rule |
|---------|-----------|------|
| Repository commits transaction | Repository only flushes | **Services commit, Repositories flush** |
| Service raises `HTTPException` | Service raises domain exception (e.g., `RecipeNotFoundError`) | Domain exceptions in services |
| Missing type hints | `def get_recipe(self, id: int) -> Recipe:` | All signatures need type hints |
| Direct model manipulation in routes | Routes → Services → Repositories → Models | Follow layered architecture |
| Pydantic v1 syntax (`class Config`) | Pydantic v2 syntax (`model_config`) | Use Pydantic v2 patterns |

### Enforcement

- **PreToolUse Hook** (`context-router.sh`) loads relevant context modules before edits
- **PostToolUse Hook** (`design-auditor.sh`) flags deterministic, grep-able violations (hardcoded colors, raw `<button>`, repo `.commit()`, etc.) via a system message — it's a fast backstop, not a full audit
- **Session Hook** (`session-init.sh`) reloads context modules after compaction

**If context feels lost during long sessions, STOP and re-read this section.**

---

## Development Commands

### Frontend (from `frontend/`)

```bash
npm run dev          # Start dev server on 0.0.0.0:3000
npm run build        # Production build
npm run lint         # ESLint
npx tsc              # TypeScript type checking
npx shadcn@latest add <component>  # Add shadcn/ui component
```

### Backend (from `backend/`)

```bash
# Activate virtual environment first
venv\Scripts\activate                          # Windows
source venv/bin/activate                       # Linux/macOS

# Run development server
python -m uvicorn app.main:app --reload --port 8001

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Seed sample data
python scripts/seed_database.py --mode replace

# Add/remove the onboarding starter pack for an existing account
python scripts/seed_sample_data.py --user-id 1 [--remove]

# Run tests
pytest
pytest tests/test_file.py -v
```

### Environment Variables

**Frontend:**
- `NEXT_PUBLIC_API_URL` - Frontend API URL (default: `http://localhost:8001`)
- `NEXT_PUBLIC_APP_URL` - Public site URL for `metadataBase`/OG tags (default: `http://localhost:3000`; set to prod URL on Railway)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Clerk auth (frontend)
- `CLERK_SECRET_KEY` - Clerk auth (frontend middleware)
- `BACKEND_URL` - Build-time target of the connector proxies (`/api/mcp`, `/api/oauth/*`, `/.well-known/oauth-*`); defaults to `NEXT_PUBLIC_API_URL`

**Backend:**
- `SQLALCHEMY_DATABASE_URL` - Backend DB URL (default: SQLite)
- `AUTH_DISABLED` - Bypass JWT for local dev (`true`/`false`)
- `DEV_USER_ID` - User ID when auth disabled (default: 1)
- `SEED_STARTER_CONTENT` - Seed the onboarding starter pack (sample recipes, meals, planner, shopping list) into new accounts on first sign-in (default: `true`; set `false` to disable)
- `CLERK_PUBLISHABLE_KEY` - Used to derive JWKS URL
- `INTEGRATION_API_KEY` - Shared secret for trusted first-party apps (X-API-Key header on `/api/shopping/external/*` and `/api/hearth/*`)
- `INTEGRATION_USER_ID` - User account all integration traffic reads from and writes to
- `GEMINI_ASSISTANT_API_KEY` - For Genie chat
- `GEMINI_TIP_API_KEY` - For cooking tips
- `GEMINI_IMAGE_API_KEY` - For image generation
- `GEMINI_RECIPE_GENERATION_API_KEY` - For AI recipe generation
- `GEMINI_NUTRITION_API_KEY` - For AI nutrition estimation
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` - Image uploads
- `GITHUB_TOKEN`, `GITHUB_REPO` - Issue tracking integration
- `STRIPE_SECRET_KEY` - Stripe API secret key (sk_xxx) for checkout/portal/customer calls
- `STRIPE_WEBHOOK_SECRET` - Signing secret (whsec_xxx) for verifying `/api/webhooks/stripe` payloads
- `STRIPE_PRICE_ID_PRO` - Price ID for the Pro subscription plan
- `FRONTEND_URL` - Base URL for Stripe checkout/portal redirects and the ChatGPT connector's OAuth issuer (default: `http://localhost:3000`)
- `MCP_ENABLED` - ChatGPT connector kill switch (default `true`); `MCP_PUBLIC_URL` / `MCP_AUTHORIZE_URL` override its origin and consent page
- `ALEXA_SKILL_ID` - Alexa skill ID(s), comma-separated; `/api/alexa` answers 404 until it's set

## Architecture

### Backend Layered Architecture

```
API Routes (app/api/)
    ↓
Services (app/services/)    # Business logic
    ↓
Repositories (app/repositories/)    # Data access
    ↓
Models (app/models/)    # SQLAlchemy ORM
```

- **DTOs** (`app/dtos/`): Pydantic models for request/response validation (21 files including AI DTOs)
- **AI Module** (`app/services/ai/`): Sub-package within services containing Gemini client, assistant (multi-turn chat with function calling), recipe generation, image generation, cooking tips, meal suggestions, and nutrition estimation
  - Never return a Gemini exception's text to the client; it names billing and project details. Services pass `e` to `ai/provider_errors.safe_ai_error(e, "<Feature>")`, which logs only the error class and numeric status and returns a safe message. Do not attach raw provider messages, details or exceptions to logs.
  - If every AI feature fails at once, check the Gemini Prepay credit balance in AI Studio first. When it's empty, every key returns `402 RESOURCE_EXHAUSTED: Your prepayment credits are depleted`.
- **Core** (`app/core/`): Auth configuration (Clerk JWKS settings)
- **Utils** (`app/utils/`): Unit conversion and dimension detection
- **Database** (`app/database/`): Connection setup and Alembic migrations (32+ migration files)
- **Router** (`app/router.py`): Centralized route registration (27 routers across 29 tags)
- **Services** use two patterns: flat files for simple services, modular packages (Core + Mixins) for complex ones (`meal/`, `planner/`, `shopping/`, `data_management/`)

#### ChatGPT connector (MCP server + OAuth 2.1)

Maryann's ChatGPT (Settings → Apps → Developer mode → custom MCP server, OAuth) reaches the app at **`https://enchantedspoon.app/api/mcp`**. One URL: the frontend proxies `/api/mcp`, `/api/oauth/*` and `/.well-known/oauth-*` to the backend (`rewrites` in `frontend/next.config.ts`, destination `BACKEND_URL` or `NEXT_PUBLIC_API_URL` at build time), and Clerk's middleware skips those paths (`proxy.ts` matcher). The issuer/origin is `MCP_PUBLIC_URL`, else `FRONTEND_URL` (`core/mcp_config.py`), never the Host header.

- **Auth:** OAuth 2.1 with DCR, PKCE S256 and RFC 9207 `iss` (`api/oauth.py` → `services/oauth_service.py` → `repositories/oauth_repo.py`, tables `oauth_clients`, `oauth_authorization_codes`, `oauth_tokens`; codes and tokens stored only as SHA-256). The authorization endpoint is the frontend page `/oauth/authorize` (behind Clerk; signed-out → `/sign-in?redirect_url=…` → back with the query). It calls `GET /api/oauth/authorize/check` and then `POST /api/oauth/authorize` with the Clerk JWT; the header is the CSRF protection. Tokens map to `users.id` from that Clerk session, so ChatGPT acts as the same account. Access 1 h, refresh 90 days sliding and rotated; a replayed code or rotated refresh token revokes the whole grant. No `openid-configuration` on purpose (ChatGPT would request every OIDC scope).
- **Kill switch:** `MCP_ENABLED=false` on the backend 404s everything. Per person: Settings → Account & Profile → Connected Apps → Disconnect (`DELETE /api/oauth/connections`).
- **Tools** (`api/mcp/tools.py`, ~125): one per user action. A tool names a route; its input schema is built from that route's OpenAPI, and `api/mcp/dispatch.py` calls the route in process on an internal copy of `api_router` whose `get_current_user` returns the token's user. So validation, read-only, usage limits and services match the app exactly. Never write SQL or duplicate service logic in a tool. **A new user-facing route needs a tool or an `EXCLUDED` reason** (`tests/test_mcp_server.py::test_every_user_route_has_a_tool` fails otherwise). AI tools say "Calls AI generation" and are marked writes so ChatGPT confirms; base64 image payloads are stripped from results (`photo_omitted`). The JSON-RPC server is hand-rolled (`api/mcp/server.py`: initialize, ping, tools/list, tools/call; stateless, JSON only), not the `mcp` SDK.
- The connector's routers are registered as `connector_router` on the public app only, outside `api_router`, so the internal dispatch app can't reach them.

#### Alexa skill ("Alexa, tell Enchanted Spoon to add a gallon of milk")

Custom skill; package and setup steps in `alexa/` (README). Amazon removed third-party access to Alexa's own shopping list in 2024, so the skill needs its invocation name. Endpoint `POST /api/alexa` on the backend's own Railway domain (not proxied, so the signed body arrives byte-for-byte), on `connector_router`. Every request is checked before it's read (`services/alexa/verification.py`): cert URL rules, the chain validated to certifi roots for `echo-api.amazon.com`, the `Signature-256` over the raw body, a timestamp within 150 s, and `ALEXA_SKILL_ID`. A failure gets a bare 400. Account linking reuses the OAuth server above. An Amazon link redirect URI (`*.amazon.com/api/skill/link/...`) is allowed in DCR, and its grants always get scope **`alexa`**. `user_for_access_token(token, scope)` keeps `alexa` tokens out of `/api/mcp` and `mcp` tokens out of `/api/alexa`. The consent page and Connected Apps word each scope. Adds go through `ShoppingService.add_named_item` on `kitchen_user_id` (household-shared, deduped, library category). `utils/spoken_items.py` parses quantities, units and "and"-separated items, and keeps "mac and cheese" or a known library ingredient whole. Read-only accounts can read but not add. **Voice pairing** (`services/alexa/link_service.py`, table `alexa_links`): an unknown Alexa account is read a six-digit, 10-minute code. Entering it in Settings → Connected Apps (`POST /api/alexa/link`) links that Alexa `userId` to the account, because the Alexa app may never show the link card. Connected Apps lists and disconnects pairings alongside OAuth grants.

#### First-party integrations (X-API-Key, not Clerk)

Trusted household apps authenticate with the shared `INTEGRATION_API_KEY` via `get_integration_user`, so every call is scoped to the single `INTEGRATION_USER_ID` account rather than the calling user. These are the only non-Clerk, non-webhook surfaces:

| Prefix | Consumer | Access |
|--------|----------|--------|
| `/api/shopping/external/*` | Tada (cleaning/chores app) | Shopping-list ingest (write) |
| `/api/hearth/*` | Hearth (family wall display) | Meal plan + meal cards + shopping list (read); writes: `POST /meals/complete` marks a plan entry cooked, `POST /shopping/items` adds one item by name |

`app/api/hearth.py` projects existing planner/meal/recipe/shopping services through `app/dtos/hearth_dtos.py` mappers — no data-access logic in the routes. Hearth deliberately cannot plan or un-complete; both stay in the app. Its shopping add (`ShoppingService.add_named_item`) is a quantity-1 manual item, deduped like Genie's adds (`add_manual_items`), and takes its category from the account's ingredient library when none is sent. Checking off, editing and removing items from the wall are not built yet.

> **Note:** Hearth's own repo is a separate workspace. Claude sessions there routinely edit this repo's backend directly, which means *this* repo's hooks and rules do not load for them — re-check branch strategy, commit trailers, and doc updates on anything that lands that way.

### Frontend Structure

- `app/` - Next.js App Router, split into route groups: `(marketing)` (public landing/privacy/terms, no app chrome), `(auth)` (bare sign-in/sign-up/sso-callback), `(app)` (dashboard, recipes, meal-planner, shopping-list, settings, admin — wrapped in AppLayout)
- `components/` - UI components organized by domain:
  - `ui/` - 32 shadcn/ui primitives (Radix-based)
  - `common/` - Shared components (StatCard, FavoriteButton, FilterBar, ChangelogDialog, etc.)
  - `layout/` - App structure (AppLayout, TopNav, MobileBottomNav, PageLayout, PageHeader)
  - `recipe/` - Recipe domain (RecipeCard, RecipeImage, RecipeBannerImage, RecipeBadge, browser/)
  - `assistant/` - AI assistant chat (Assistant, AssistantPopup, ChatMessageList)
  - `auth/` - Authentication (SignInForm, SignUpForm — the user menu lives inline in TopNav)
  - `forms/` - Form inputs (IngredientAutocomplete, QuantityInput, QuickAddForm)
- `hooks/` - Custom React hooks organized by domain:
  - `hooks/api/` - React Query hooks for all API calls (14 files + queryKeys factory)
  - `hooks/forms/` - Form-specific hooks (filters, autocomplete, feedback)
  - `hooks/persistence/` - localStorage hooks (settings, chat history, recent recipes, filter state, unit conversion)
  - `hooks/ui/` - UI behavior hooks (drag-and-drop, chat scroll, unsaved changes)
- `lib/` - API client, utilities, constants, providers:
  - `lib/api/` - Domain-split API modules with barrel re-export (18 modules)
  - `lib/providers/` - React Context providers (QueryProvider, NavActionsProvider, RecipeWizardProvider, AssistantProvider)
  - `lib/api-client.ts` / `lib/api-server.ts` - Authenticated fetch wrappers
  - Utilities: filterUtils, formValidation, imageUtils, quantityUtils, recipeCardMapper, config, constants
- `types/` - TypeScript types split by domain (recipe.ts, meal.ts, planner.ts, shopping.ts, ai.ts, common.ts, category.ts, ingredient-settings.ts, admin.ts)
- `data/` - Static data (changelog entries)
- `proxy.ts` - Clerk auth middleware

### Key Patterns

**API Client** (`lib/api/`): Domain-split API modules with barrel re-export:
```typescript
// All imports go through the barrel index
import { recipeApi, plannerApi, shoppingApi, AssistantApi, ... } from "@/lib/api";

// 18 modules: base.ts, recipe.ts, planner.ts, shopping.ts, ai.ts,
// ingredients.ts, upload.ts, dashboard.ts, data-management.ts,
// feedback.ts, units.ts, settings.ts, recipe-groups.ts, categories.ts,
// ingredient-categories.ts, ingredient-units.ts, admin.ts
```

**API Authentication Layer**:
- `lib/api-client.ts`: Client-side authenticated fetch with Clerk token injection
- `lib/api-server.ts`: Server-side authenticated fetch for RSC

**State Management**:
- Server state: React Query (hooks in `hooks/api/`)
- Local state: React useState
- Form state: React Hook Form + Zod validation schemas
- Context state: React Context providers (RecipeWizardProvider, AssistantProvider, NavActionsProvider)
- Persisted state: Custom hooks with localStorage (in `hooks/persistence/`: `useSettings`, `useChatHistory`, `useRecentRecipes`, `useRecipeFilterPersistence`, `useUnitConversionRules`)

**Form Components**: Use React Hook Form with Zod schemas and shadcn/ui components. Never hardcode colors.

## Design System (CRITICAL)

This project has an extensive design system. **Always follow these rules**:

1. **Use shadcn/ui components** - Never create fake cards, buttons, or badges with raw divs
2. **Use semantic color tokens** - `text-muted-foreground`, `bg-card`, `border-border` (not `text-gray-500`)
3. **Use Tailwind scale** - `h-10`, `gap-4` (not `h-[38px]`, `gap-[15px]`)
4. **Icon buttons need aria-label** - `<Button size="icon" aria-label="Close">`
5. **Loading states required** - Buttons show spinner + disabled during async actions

**Quick Reference - When to use what**:
| Need | Use |
|------|-----|
| Card container | `<Card>` from `@/components/ui/card` |
| Button | `<Button variant="..." size="...">` |
| Badge/status | `<Badge variant="...">` |
| Form input | `<Input>`, `<Select>`, `<Textarea>` from ui/ |
| Icon | Lucide React with `strokeWidth={1.5}` |

## Authentication

- **Provider**: Clerk (configured in `proxy.ts`)
- **Client-side**: `lib/api-client.ts` injects Clerk tokens automatically
- **Server-side**: `lib/api-server.ts` for React Server Components
- **Protected routes**: Backend validates JWT tokens on all authenticated endpoints

## Key Domain Models

### Backend Models (17 model files)
- **User** - Clerk-integrated user with subscription management (`has_pro_access` property), admin flag, cascade relationships to all data
- **Recipe** - Full recipe with ingredients, directions, dual images (reference + banner), `total_time` hybrid property (prep + cook)
- **RecipeIngredient** - Junction table (recipe <-> ingredient)
- **Ingredient** - Global ingredient master (user_id nullable for system ingredients)
- **NutritionFacts** - Per-recipe nutrition data (calories, macros, vitamins)
- **RecipeHistory** - Cooking history tracking (recipe_id, cooked_at, notes)
- **RecipeGroup** - Recipe collections/folders
- **Meal** - Composition of main recipe + up to 3 side recipes (transient meals auto-deleted with planner entries)
- **PlannerEntry** - Meal in the weekly planner (max 20 incomplete entries, soft-delete via `is_cleared` for streak tracking)
- **ShoppingItem** - Shopping list item with aggregation_key for diff-based sync
- **ShoppingItemContribution** - Source tracking (which recipes contribute to each shopping item)
- **UnitConversionRule** - Conversion rules (from_unit, to_unit, factor)
- **UserSettings**, **UserCategory**, **UserIngredientCategory**, **UserIngredientUnit** - User customization models
- **UserUsage** - AI feature usage tracking per user

### Frontend Types (9 type files)
- **RecipeCardDTO** / **RecipeCardData** - Lightweight recipe for lists
- **MealSelectionResponseDTO** - Meal with hydrated recipes
- **PlannerEntryResponseDTO** - Planner entry with meal data
- **ShoppingMode** - "all" | "produce_only" | "none"
- **AssistantMessage** / **AssistantRequestDTO** / **AssistantResponseDTO** - AI chat types
- **RecipeGeneratedDTO** - AI-generated recipe output
- **ImageGenerationRequestDTO** / **ImageGenerationResponseDTO** - Image generation types

## Constraints & Limits

| Feature | Limit |
|---------|-------|
| Planner entries | 20 max (incomplete only — completed meals awaiting clear don't count) |
| Side recipes per meal | 3 max |
| Meal tags | 20 max, 50 chars each |
| Recipe/Ingredient name | 255 chars |

## API Conventions

- All endpoints return standardized Pydantic DTOs
- Error responses follow FastAPI HTTPException patterns
- List endpoints support pagination via `skip`/`limit` parameters
- Dates stored as ISO 8601 strings (YYYY-MM-DD)

## Testing

**Backend**: pytest with fixtures in `tests/`
**Frontend**: Manual testing with dev server

## MCP Servers Available

- `shadcn` - Search and add shadcn/ui components
- `next-devtools` - Next.js MCP tools (requires dev server running)
- `cloudinary-asset-mgmt` - Image upload and management
- `claude-code-docs` - Access Claude Code documentation

## Claude Code Skills & Commands

### ⚠️ Automatic Context System (Hook-Based)

**Context is loaded automatically via hooks when you edit files. No manual action needed.**

The project uses **command-based hooks** (fast shell scripts, not agents) to load context automatically:

**Hook Lifecycle:**
1. **SessionStart** (on compaction) → Reload context modules
2. **PreToolUse** (before Edit/Write) → Load relevant context modules
3. **PostToolUse** (after Edit/Write) → Flag deterministic design-system violations
4. **Stop** → Run ESLint on changed files, block stop on errors

**Context Modules** (`.claude/context/`):
- **Frontend** (9): frontend-core, design-tokens, shadcn-patterns, component-patterns, component-inventory, form-patterns, layout-patterns, accessibility, data-fetching, structure
- **Backend** (9): backend-core, architecture, models, repositories, services, dtos, routes, migrations, exceptions

**Performance**: 1 shell script per edit (~<1s) vs 3 agent spawns (~90s)

**Requirements**: jq (JSON parser) and Git Bash (Windows)

For detailed troubleshooting and configuration, see [.claude/HOOKS.md](.claude/HOOKS.md)

### Specialized Agents

- `frontend-designer` - React/Next.js component and layout work, design system compliance
- `backend-architect` - FastAPI layered architecture (DTOs → Services → Repositories → Models)
- `auditor` - Single-file compliance audit against criteria checklists (invoked by `/audit`)

### Commands

- `/git` - Git workflow automation, no PRs or approval stops (start, commit, sync, merge, deploy, backport, cleanup, status)
- `/todo` - Generate TODO items
- `/changelog` - Generate changelog entries

## Deployment

Uses Railway with Dockerfiles in `frontend/` and `backend/` directories. Configuration in `railway.json`.


## Soft-launch guardrails (October 2026)

- Images are opt-in. RecipeGenerationService accepts a metered image callback; never
  restore direct provider-image calls there. Optional images use `ai/optional_images.py`
  and atomically reserve `ai_images_generated` before spending. One unit means a photo
  action (up to a square/banner pair), including single-image regenerations.
- Launch allowances live in `core/usage_limits.py`; keep public pricing and usage labels
  consistent. These are feature allowances, not a guarantee on provider invoice totals.
- Persisted User.usage_plan keeps existing accounts on legacy allowances. New ORM
  accounts use launch allowances; use get_user_monthly_limit for enforcement and display.
  Never silently migrate legacy users to lower limits.
- Feedback must verify a private GitHub destination before publishing. Do not remove
  the fail-closed check to make a public issue tracker work.
- Production checkout requires live key configuration, webhook secret and HTTPS return
  origin. Production webhook verification rejects test-mode events.
- `npm run build` uses webpack for Windows-compatible standalone output. Run frontend
  tests as well as lint/build. Backend async tests use anyio with the asyncio backend.
  Use the `file_db` fixture for code that commits/rolls back; in-memory transaction
  fixtures can lose their seeded users on rollback. If pytest's shared Windows temp
  symlink is inaccessible, use a fresh task-local `--basetemp`, not permission changes.
- Release gates and what was actually tested: `docs/soft-launch-readiness.md`.
