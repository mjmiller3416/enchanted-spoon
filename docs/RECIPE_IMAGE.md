# Recipe Image System

Reference for how recipe images move through the app: dual-image strategy, Cloudinary
addressing, AI generation entry points, and frontend display. For prop-level component APIs
read the source files directly.

---

## Overview

Every recipe has two independent images:

| Image | Aspect ratio | Purpose |
|-------|-------------|---------|
| **Reference** (`reference_image_path`) | 1:1 square | Cards, thumbnails, circular avatars |
| **Banner** (`banner_image_path`) | 21:9 ultrawide | Hero section on the recipe detail page |

Both are nullable — a recipe can have either, both, or neither. Images come from two sources:
**AI-generated** (Google Gemini image model) or **user-uploaded** (file picker). Both paths
converge on the same Cloudinary upload pipeline. All images are served from Cloudinary; nothing
is stored on disk.

---

## Cloudinary addressing — keyed by `image_key`, not the recipe's primary key

Every `Recipe` has a stable `image_key` (UUID, `models/recipe.py`), separate from its
auto-increment `id`. **Cloudinary paths are always built from `image_key`:**

```
meal-genie/recipes/{image_key}/
  reference_{image_key}.jpg
  banner_{image_key}.jpg
```

Why: the primary key is mutable across environments (a recipe that's `id=12` in local SQLite
might be `id=340` in prod Postgres) and can be reassigned if a recipe is deleted/recreated.
`image_key` doesn't change. It's also what lets a recipe **move** between groups/users keep its
images while a **copy** gets a fresh key (and thus fresh images) — see the resolution logic in
`app/api/upload.py::_resolve_image_key`, which looks the key up server-side from the recipe the
caller owns (this also enforces that users can only upload to their own recipes).

The `meal-genie/` folder prefix is a fixed Cloudinary namespace — it doesn't track the app's
"Assistant" rename and doesn't need to.

**Key files:**
- `backend/app/api/upload.py` — `POST /api/upload` (file), `POST /api/upload/base64` (base64,
  used for AI-generated images), `DELETE /api/upload/{public_id}`
- `backend/app/services/data_management_service.py` — deletes Cloudinary images before the DB
  row on recipe/account deletion (`_extract_cloudinary_public_id`, `_delete_cloudinary_images`)

---

## AI image generation

Three entry points, all ultimately calling `app/services/ai/image_generation/service.py`
(`get_image_generation_service()`), pro-gated (`require_pro`):

| Entry point | Endpoint | Notes |
|---|---|---|
| Standalone generation (recipe add/edit form) | `POST /api/ai/image-generation` | `image_type: "both" \| "reference" \| "banner"`. `"both"` calls `generate_dual_recipe_images()`; single-type calls `generate_recipe_image()` with the matching prompt template + aspect ratio. |
| Banner from an existing reference image | `POST /api/ai/image-generation/banner` | Takes a base64 reference image, generates a matching banner via `generate_banner_from_reference()` — keeps the same dish/styling instead of re-prompting from scratch. |
| Assistant recipe drafts | `POST /api/ai/assistant/chat` (or the legacy `/generate-recipe` alias) | `AssistantRecipeRequestDTO.generate_image` triggers `generate_dual_recipe_images()` inline during recipe drafting. |
| AI recipe generation wizard (Pro) | `POST /api/ai/wizard-generation` | `RecipeGenerationRequestDTO.generate_image` (singular) — same dual-image call, alongside optional nutrition estimation. |

All four return **base64-encoded PNG data** (`reference_image_data` / `banner_image_data`), not
URLs — nothing is uploaded to Cloudinary until the user accepts the result and submits the form
(`useRecipeForm` converts base64 → `File` → uploads via the normal `/api/upload` pipeline).
Image generation failures are non-fatal everywhere: the recipe/text response still returns, with
the image fields left `null`.

Each AI image call increments `ai_images_generated` via `UsageService` (silent-fail — usage
tracking never blocks the feature).

**Config:** prompt templates, aspect ratios, and output sizes live in
`app/services/ai/image_generation/config.py`. Env var: `GEMINI_IMAGE_API_KEY`.

---

## Cloudinary transformations

Upload-time (`app/api/upload.py`): `quality: auto:good`, `fetch_format: auto` (auto WebP/AVIF).

Display-time (`frontend/src/lib/imageUtils.ts`) — the frontend inserts a transformation segment
into the URL after `/upload/`; Cloudinary generates the derivative on first request and caches
it at the edge (~30 day TTL) after that:

| Function | Use | Params |
|---|---|---|
| `getRecipeImageUrl(path)` | Validates/normalizes a raw path; returns `undefined` for local filesystem paths or empty values (shows placeholder) | — |
| `getHeroBannerUrl(url)` | Recipe detail hero | `w_1600,h_686,c_fill,g_auto/q_auto` (21:9) |
| `getRecipeCardUrl(url, w=400, h=300)` | Card/grid thumbnails | `w_{w},h_{h},c_fill,g_auto` |
| `getBannerUrl(url, w=1200, h=400)` | Wide non-hero contexts | `w_{w},h_{h},c_fill,g_auto/q_auto` |

`g_auto` = Cloudinary's AI subject-detection gravity, so crops stay centered on the food rather
than an arbitrary corner. Non-Cloudinary URLs (e.g. local dev fallback paths) pass through all
four functions unchanged.

---

## Frontend display components

`RecipeImage` (`components/recipe/RecipeImage.tsx`) is the foundation every other image
component wraps — it owns error handling (`onError` → `ChefHat` placeholder), the empty-state
placeholder (`src` is null/undefined), and an optional fade-in transition (`showLoadingState`,
default `true`; set `false` in dense grids to skip the animation overhead).

| Component | Wraps | Purpose |
|---|---|---|
| `RecipeBannerImage` (`components/recipe/RecipeBannerImage.tsx`) | `RecipeImage` | Wide contexts. Prefers `bannerSrc` (`getBannerUrl`), falls back to `fallbackSrc` (the reference image, cropped via `getRecipeCardUrl`) when no banner exists. |
| `CircularImage` (`components/common/CircularImage.tsx`) | `RecipeImage` | Fixed circular sizes (sm/md/lg/xl), passes a smaller icon via `iconClassName`. |
| `RecipeHeroImage` (`app/(app)/recipes/[id]/_components/detail/RecipeHeroImage.tsx`) | — | Recipe detail hero; only consumer is `FullRecipeView`. |

**Current consumers of `RecipeImage`/`CircularImage` directly:** `RecipeCard`, `MealGridCard`,
`SelectedMealCard`, `SavedMealCard`, `MealPreviewPanel`, `CompletedDropdown`, `MealQueueItem`
(dashboard), `RecipeHeroImage`. Grep for `RecipeImage|CircularImage` under `frontend/src` if this
list drifts — components here get renamed/deleted more often than this doc gets updated.

**Upload UI:** `ImageUploadCard` (`app/(app)/recipes/_components/shared/ImageUploadCard.tsx`) —
handles both file upload and "Generate with AI" in the recipe add/edit form. User's custom
AI prompt override is stored in `localStorage` (`enchanted-spoon-settings`, via `useSettings`) and
must contain a `{recipe_name}` placeholder.

---

## Types

Backend DTOs: `app/dtos/image_generation_dtos.py`. Frontend types: `frontend/src/types/ai.ts`
(not a single `types/index.ts` — types are domain-split; image generation types live alongside
the other AI feature types: `ImageGenerationRequestDTO`, `ImageGenerationResponseDTO`,
`BannerGenerationResponseDTO`, plus the image fields on `AssistantRecipeResponseDTO` and
`RecipeGenerationResponseDTO`).

---

## Known gaps

- The assistant now lives at `/api/ai/assistant/*` (the pre-rename `/api/ai/meal-genie/*` prefix
  is aliased for one release, then goes away). `/api/ai/wizard-generation` is still the live
  prefix for the AI recipe-generation wizard — it has a `# TODO: rename` comment in `router.py`
  pending a frontend change; don't be surprised that path doesn't match the feature name.
