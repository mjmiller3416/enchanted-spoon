# Enchanted Spoon Frontend Documentation

Architecture decisions and patterns for the Next.js frontend. For component APIs, types, and hooks, read the source files directly.

## Tech Stack

- **Next.js 16** with App Router
- **React 19** with React Query 5 for server state
- **TypeScript 5** for type safety
- **Tailwind CSS 4** with CSS variables for theming
- **shadcn/ui** (New York style) built on Radix UI (32 components)
- **React Hook Form 7** + **Zod 4** for form state & validation
- **dnd-kit** for drag-and-drop
- **Framer Motion** for animations
- **Clerk** for authentication
- **Lucide React** for icons (strokeWidth={1.5})
- **Sonner** for toast notifications
- **react-markdown** for markdown rendering

## Directory Structure

```
src/
├── app/                      # Next.js App Router pages, split into route groups
│   ├── (marketing)/          # Public landing page, privacy/terms, /whats-new — no app chrome
│   ├── (auth)/               # Clerk sign-in/sign-up/sso-callback — bare, centered, no app chrome
│   ├── (app)/                # Everything behind auth, wrapped in AppLayout:
│   │   ├── dashboard/        #   Home — today-first (Tonight card), single surface for all viewports
│   │   ├── recipes/          #   Recipe browser, detail, add (wizard)
│   │   ├── meal-planner/     #   Meal planner (MealCreationOverlay is the one meal-creation surface)
│   │   ├── shopping-list/    #   Shopping list with categories
│   │   ├── settings/         #   User settings (appearance, data, AI, etc.)
│   │   └── admin/            #   Admin dashboard (users, database)
│   ├── api/upload/           # File upload API route
│   ├── not-found.tsx / error.tsx / global-error.tsx   # Branded route boundaries
│   ├── layout.tsx            # Root layout (ClerkProvider, QueryProvider, Toaster, blocking theme script)
│   └── globals.css           # Design tokens & global styles (dark theme)
├── components/
│   ├── ui/                   # shadcn/ui primitives (32 components — don't modify)
│   ├── common/               # Shared across pages (StatCard, FavoriteButton, FilterBar, ChangelogDialog, etc.)
│   ├── layout/               # App structure (AppLayout, TopNav, MobileBottomNav, PageLayout, PageHeader)
│   ├── recipe/               # Recipe domain (RecipeCard, RecipeImage, RecipeBadge, browser/)
│   ├── assistant/            # AI assistant chat (Assistant, AssistantPopup, ChatMessageList)
│   ├── auth/                 # Authentication (SignInForm, SignUpForm — the user menu lives inline in TopNav)
│   └── forms/                # Form inputs (IngredientAutocomplete, QuantityInput, QuickAddForm)
├── hooks/
│   ├── api/                  # React Query hooks (14 files + queryKeys factory)
│   ├── persistence/          # localStorage hooks (settings, chat history, recent recipes, filters, units)
│   ├── forms/                # Form hooks (filters, autocomplete, feedback)
│   └── ui/                   # UI behavior hooks (drag-and-drop, chat scroll, unsaved changes)
├── lib/
│   ├── api/                  # Domain-split API modules (18 modules with barrel re-export)
│   ├── providers/            # React Context (QueryProvider, NavActionsProvider, RecipeWizardProvider, AssistantProvider)
│   ├── api-client.ts         # Client-side authenticated fetch (Clerk token injection)
│   ├── api-server.ts         # Server-side authenticated fetch (RSC)
│   ├── config.ts             # App configuration
│   ├── constants.ts          # Dropdowns, categories, static data
│   ├── filterUtils.ts        # Recipe filtering logic
│   ├── formValidation.ts     # Zod validation schemas
│   ├── imageUtils.ts         # Image processing utilities
│   ├── quantityUtils.ts      # Quantity conversion utilities
│   ├── recipeCardMapper.ts   # DTO → UI model mapping
│   └── utils.ts              # cn() and other utilities
├── types/                    # TypeScript types split by domain
│   ├── recipe.ts             # Recipe DTOs & filters
│   ├── meal.ts               # Meal types
│   ├── planner.ts            # Planner types
│   ├── shopping.ts           # Shopping list types
│   ├── ai.ts                 # AI feature types (assistant, generation, tips)
│   ├── common.ts             # Shared types (import/export, backup)
│   ├── category.ts           # Category types
│   ├── ingredient-settings.ts # Ingredient settings types
│   └── admin.ts              # Admin types
├── data/
│   └── changelog.ts          # Version history data
└── proxy.ts                  # Clerk auth middleware
```

## Key Patterns

### Page Structure

Pages live in `app/(app)/[page]/page.tsx` (or `(marketing)`/`(auth)` for public routes). Page-specific components go in `app/(app)/[page]/_components/`. Shared components go in `components/`.

```typescript
// app/(app)/recipes/page.tsx
export default function RecipesPage() {
  return <RecipeBrowser />;
}

// app/(app)/recipes/_components/RecipeBrowser.tsx
// Complex page-specific component
```

### Component Organization

| Directory | Purpose | Examples |
|-----------|---------|----------|
| `ui/` | shadcn primitives — don't edit | Button, Card, Dialog, Sheet, Tabs |
| `common/` | Reusable across pages | StatCard, FavoriteButton, FilterBar, ChangelogDialog |
| `recipe/` | Recipe domain components | RecipeCard, RecipeBadge, RecipeImage, RecipeBannerImage |
| `layout/` | App structure | AppLayout, TopNav, MobileBottomNav, PageHeader, PageLayout |
| `assistant/` | AI chat interface | Assistant, AssistantPopup, ChatMessageList |
| `auth/` | Authentication UI | SignInForm, SignUpForm |
| `forms/` | Specialized inputs | IngredientAutocomplete, QuantityInput, QuickAddForm |

### API Layer

All backend calls go through `lib/api/` modules. Never call fetch directly in components.

```typescript
// lib/api/ - Domain-split API modules with barrel re-export
import { recipeApi, plannerApi, shoppingApi } from "@/lib/api";

// Each module exports an object with typed CRUD methods:
export const recipeApi = {
  listCards: (filters?) => fetchApi<RecipeCardDTO[]>("/api/recipes/cards", ...),
  get: (id: number) => fetchApi<RecipeResponseDTO>(`/api/recipes/${id}`),
  create: (data: RecipeCreateDTO) => fetchApi("/api/recipes", { method: "POST", body: data }),
  // ...
};

// 18 modules: base, recipe, planner, shopping, ai, ingredients, upload,
// dashboard, data-management, feedback, units, settings, recipe-groups,
// categories, ingredient-categories, ingredient-units, admin
```

### React Query Hooks

Wrap API calls in hooks for components. All hooks in `hooks/api/`.

```typescript
// hooks/api/useRecipes.ts
export function useRecipeCards(filters?: RecipeFilters) {
  return useQuery({
    queryKey: ["recipes", "cards", filters],
    queryFn: () => recipeApi.listCards(filters),
  });
}

// In components
const { data: recipes, isLoading } = useRecipeCards(filters);
```

**Naming conventions:**
- `useXxx` — query hook (fetches data)
- `useCreateXxx`, `useUpdateXxx`, `useDeleteXxx` — mutation hooks
- `useToggleXxx` — toggle mutation

### Types

Types are split across 9 domain files in `types/` (recipe.ts, meal.ts, planner.ts, shopping.ts, ai.ts, common.ts, category.ts, ingredient-settings.ts, admin.ts). Types mirror backend DTOs with some frontend-specific mappings.

```typescript
// Backend DTO format (snake_case)
interface RecipeCardDTO {
  id: number;
  recipe_name: string;
  is_favorite: boolean;
}

// Frontend mapped format (camelCase) - used in some components
interface RecipeCardData {
  id: number;
  name: string;
  isFavorite: boolean;
}
```

## Styling & Theming

### Design Tokens

All colors defined as CSS variables in `globals.css`. **Never use hardcoded Tailwind colors.**

```css
/* globals.css */
:root {
  --background: #0f0f14;
  --foreground: #f1f0f5;
  --primary: #8b5cf6;      /* Purple */
  --secondary: #14b8a6;    /* Teal */
  --muted: #1e1e2a;
  /* ... */
}
```

```tsx
// ✅ Correct - uses semantic tokens
<div className="bg-background text-foreground border-border">

// ❌ Wrong - hardcoded colors
<div className="bg-gray-900 text-gray-100 border-gray-700">
```

### Class Merging

Use `cn()` for conditional classes:

```typescript
import { cn } from "@/lib/utils";

<Button className={cn("base-class", isActive && "active-class")} />
```

### shadcn/ui Components

Add new components via CLI:

```bash
npx shadcn@latest add button dialog card
```

Components install to `components/ui/`. Don't modify these directly — extend with wrapper components if needed.

## File Reference

| Need to... | Look in... |
|------------|------------|
| Add a page | `src/app/` |
| Add shared component | `src/components/common/` |
| Add API method | `src/lib/api/` (domain-split module) |
| Add React Query hook | `src/hooks/api/` |
| Add TypeScript type | `src/types/` (domain-split file) |
| Add constant/dropdown | `src/lib/constants.ts` |
| Add form validation | `src/lib/formValidation.ts` (Zod schemas) |
| Add Context provider | `src/lib/providers/` |
| Modify design tokens | `src/app/globals.css` |

## Reference Files

For code patterns, look at existing implementations:

| Pattern | Reference |
|---------|-----------|
| Page with filters | `app/(app)/recipes/page.tsx` |
| Recipe browser | `components/recipe/RecipeBrowserView.tsx` |
| Multi-step wizard | `app/(app)/recipes/_components/wizard/RecipeWizardView.tsx` |
| API hooks | `hooks/api/useRecipes.ts` |
| Form with validation | `app/(app)/recipes/_components/wizard/wizardSchema.ts` |
| Drag-and-drop | `app/(app)/meal-planner/_components/` |
| AI integration | `components/assistant/` |
| Admin panel | `app/(app)/admin/_components/AdminView.tsx` |
| Print layout | `app/(app)/recipes/[id]/_components/print/` |

## Gotchas

**Client vs Server components:** Pages are server components by default. Add `"use client"` for hooks, state, or browser APIs.

**Image optimization:** Use `RecipeImage` component which handles fallbacks. For static images, use Next.js `Image` from `next/image`.

**Form state:** Complex forms use React Hook Form + Zod schemas (see recipe wizard). Simple forms may use controlled `useState`. Validation schemas in `lib/formValidation.ts`.

**Clerk auth:** Middleware in `src/proxy.ts`. API calls automatically include auth token via the authenticated fetch wrapper in `lib/api-client.ts`.

**React Query keys:** Use the `queryKeys` factory in `hooks/api/queryKeys.ts`. Always include filter params for proper cache invalidation.

**Mobile vs Desktop:** No device fork anymore. `/` server-redirects signed-in users to `/dashboard` (Home) regardless of viewport — Home is responsive, not device-forked. `(marketing)`/`(auth)`/`(app)` route groups control chrome: only `(app)` renders `AppLayout` (TopNav + MobileBottomNav); marketing and auth pages render bare.

**Card component:** The `<Card>` component has `flex-col` as a base style. When you need horizontal layout inside a Card, explicitly add `flex-row`.