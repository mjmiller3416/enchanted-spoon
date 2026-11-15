# Photo import

A person snaps or uploads a photo of a recipe card or cookbook page and gets a
draft recipe they can review and edit before anything is saved.

This document is the engineering spec. Product copy in the app must not use
the words "AI", "artificial intelligence", "GPT", or "Gemini". Use "Snap a
recipe" and "Import from photo".

## What already exists

URL import, TikTok, and Instagram share one pipeline:

- `POST /api/ai/recipe-import` returns `RecipeImportResponseDTO` (a
  `RecipeGeneratedDTO` plus optional nutrition and a source photo). Nothing is
  saved until the wizard's existing Save.
- Website pages use recipe-scrapers, then one normalization call. Social posts
  use the public caption (or `pasted_text` when the caption cannot be read)
  and the same normalizer. The JSON shape is `parse_recipe_dict`.
- The normalizer uses `GEMINI_LITE_MODEL` (default `gemini-3.1-flash-lite`,
  overridable) and `GEMINI_RECIPE_GENERATION_API_KEY`. Token counts go to the
  `gemini_usage` log. Prompt text is not logged.
- `require_within_usage_limit("recipes_imported")` reserves one import before
  the work and releases it if the handler raises. Caps: Pro 50/month (100 for
  a usage-exempt Pro account, ×1.5 when a household of 2+ pools on the owner),
  trial 5 for the whole trial, legacy free 5/month, expired / read-only /
  `none` blocked. `none` returns 403 `trial_required` ("Start your 7-day
  trial") before a unit is reserved. Read-only returns 403 `read_only`.
- Per-minute limits run before that reservation: 5/minute per user and
  15/minute per IP (`GENERATION_USER_LIMITS`, `GENERATION_IP_LIMITS`), matching
  the route decorators.
- Recipe photos that are kept live in Cloudinary, uploaded with
  `POST /api/upload` only after a recipe exists, keyed by `image_key`. URL
  import downloads the page's photo (10 MB cap) and returns it as base64 so
  the client can upload it later. That path is not used here.

The wizard already turns a `RecipeImportResponseDTO` into the review screens:
Recipe Basics, Ingredients, Directions & Notes, Nutrition. Save is a separate
request. Creation methods today are manual, link URL, and the prompt flow.
`@capacitor/camera` is not installed. The native apps are a Capacitor shell
around the hosted site.

## UX

Hidden until the web flag in phase 2 is on. The API flag below stays off until
then too.

1. New recipe → Choose method → **Import from photo**. Description: "Snap a
   recipe card or cookbook page. You can review and edit everything before
   saving."
2. **Snap a recipe** opens the camera. **Choose photos** opens the library.
   Up to **4** photos of the same recipe, in page order. Thumbnails, remove,
   and a count ("2 of 4"). Web uses
   `<input type="file" accept="image/jpeg,image/png,image/webp">`, with
   `capture="environment"` on the snap button. Capacitor uses
   `@capacitor/camera` (phase 3).
3. Submit sends one multipart request (`images`, repeated, plus optional
   `allowed_categories`). The button shows a spinner and stays disabled.
4. Success uses the URL-import handoff: prefill the wizard, switch to the
   manual steps, toast `"{name}" imported — review and edit below.` Local
   thumbnails stay on the device for that screen. Nothing is saved until Save.
   There is no source URL. Nutrition stays empty; the existing nutrition step
   still works.
5. Errors stay on the photo step, except the gates below, which open the
   existing paywall (`recipes_imported` is already labeled "recipe imports"):
   - Unreadable, empty, or not JPEG/PNG/WebP: "Use a JPEG, PNG, or WebP photo."
   - Over 10 MB, or still too big after compression: the 413 / 400 text from
     the API.
   - More than 4: "You can import up to 4 photos at a time."
   - No recipe in the photos: 422, "No recipe was found in that photo." (or
     "those photos"). The draft is not created.
   - `trial_required`, `read_only`, `usage_limit_exceeded`: existing paywall.
   - Anything else: "We couldn't read those photos. Please try again." The
     import unit is refunded.

HEIC from an iPhone library is rejected by the server. Phase 3 asks the camera
plugin for JPEG so the phone converts it. The web file picker lists JPEG, PNG,
and WebP. No new image library.

## API (phase 1, this change)

`POST /api/ai/recipe-import/photo`

Multipart form:

| Field | Rule |
| --- | --- |
| `images` | 1 to 4 files. JPEG, PNG, or WebP. 10 MB each before compression. |
| `allowed_categories` | Optional comma-separated list. Empty means the caller's enabled categories, same as URL import. |

Response is `RecipeImportResponseDTO` with `nutrition_facts`, `source_url`,
`reference_image_data`, and `banner_image_data` all null. The recipe is the
same `RecipeGeneratedDTO` URL import returns. No recipe row is written.

`PHOTO_IMPORT_ENABLED` defaults off. Unset, `false`, or any other value →
**404** "Photo import is not available." That check runs before the import is
reserved and before the photos are parsed. Truthy values: `1`, `true`, `yes`,
`on`.

Each accepted request reserves **exactly one** `recipes_imported` unit, whether
it contains 1 photo or 4. The handler does not loop the meter. A 400, 413,
422, or 500 releases that unit. The 5/minute and 15/minute limits are the same
ones URL import uses, and they run before the reservation.

### Images

In memory only, on a worker thread:

- Reject empty files, non-photos, and images over 20 megapixels.
- Apply orientation, drop EXIF (including location), flatten transparency onto
  white, scale the long edge to 1600 px.
- Encode JPEG at quality 85, then 70, then 55, and stop once the file is at
  most 1.5 MB. If it is still larger, 400.

One model call receives every JPEG, in order, plus the prompt. Output is JSON
(`response_mime_type: application/json`, `thinking_level: minimal`,
`max_output_tokens: 8192`) parsed by `parse_recipe_dict`. The prompt's keys
match the URL-import prompt, including `no_recipe_found`.

### Model

`PHOTO_IMPORT_MODEL` in `backend/app/services/ai/recipe_import/config.py` is the
literal `gemini-3.1-flash-lite`. It does **not** follow `GEMINI_LITE_MODEL`, so
an override for the other lite calls cannot change photo extraction. Changing
the model is a code change to that constant. The key is the existing
`GEMINI_RECIPE_GENERATION_API_KEY`. No new key, and no Railway variable is set
by this work.

One `gemini_usage` line per request: `feature=photo_import`, the pinned model,
and token counts. Prompt text and photo bytes are not logged.

### Cost

Paid standard list price for `gemini-3.1-flash-lite` (Google AI pricing page,
last updated 2026-10-30): **$0.25 / 1M input tokens** for text and images,
**$1.50 / 1M output tokens** including thinking tokens.
<https://ai.google.dev/gemini-api/docs/pricing>

The page does not publish a tokens-per-image figure for this model. Until
`gemini_usage` samples exist, budget **1,600 input tokens per compressed page**
and **~700 tokens of prompt**, plus **~1,500 output tokens** for one recipe:

| Request | Planning budget |
| --- | --- |
| 1 photo | about $0.003 |
| 4 photos | about $0.004 |
| 4 photos that hit the 8,192 output cap | about $0.014 |

Output dominates, so four pages are not four times the cost. A failed call can
still be billed by the provider; the import unit is refunded anyway, and the
per-minute limits cap repeats. At the Pro cap of 50 imports, all 4-photo, the
planning budget is about **$0.20 / user / month**. A trial (5 imports) is about
**$0.02**. This spends the same `recipes_imported` allowance as a link import.
It does not add a new cap. Do not turn the flag on until a few real
`gemini_usage` lines sit inside this budget. If a page is several times over,
shrink `MAX_PHOTO_EDGE_PX` before rollout. Do not switch models by setting a
Railway variable.

## Privacy

Enchanted Spoon does not store the source photo. It is not written to the
database, to disk, to Cloudinary, or to logs, and it is not returned in the
response. The re-encode drops camera metadata before the call. The compressed
JPEG exists only for that request and is then discarded.

The compressed JPEG is sent to the model provider as the request body. This
app does not control the provider's retention.

The review screen (phase 2) shows the files the browser or the phone still
has. Saving the recipe does not upload them. A later, separate change can let
someone keep a photo as the recipe image by sending that local file through
the existing `POST /api/upload` after the recipe id exists.

## Tests and rollout

Phase 1 tests (model call mocked):

- The constant is the literal `gemini-3.1-flash-lite`, and the call uses it
  rather than `GEMINI_LITE_MODEL`.
- 4 photos → one `generate_content` call, four JPEG parts, one
  `gemini_usage` line, one `recipes_imported` increment, no recipe row, no
  Cloudinary upload, no photo bytes in the response or the log.
- 5 photos, an unreadable file, and "no recipe" → no lasting import unit.
- Flag off → 404 and `reserve` is not called.
- Flag on, account with no allowance → 403 `trial_required` and no usage row.
- Compression: PNG becomes a JPEG, a wide image is scaled to 1600 px, a
  non-photo and an 10 MB+ file are rejected.

Rollout stays off in production. `PHOTO_IMPORT_ENABLED` is not set on Railway
by this change. The web flag (`NEXT_PUBLIC_PHOTO_IMPORT_ENABLED`, phase 2)
is compiled into the hosted bundle, which is what the Capacitor shell loads,
so turning the button on is a frontend deploy. Turn the API flag on only in
staging first, compare `gemini_usage` to the budget above, then production.
Both flags default off, so a deploy of the code does not expose the feature.

## Phases

| Phase | PR | In it | Out of it |
| --- | --- | --- | --- |
| 1 | This PR | Plan, `POST /api/ai/recipe-import/photo`, 1–4 photos, one import unit, pinned model, flag default off, gating, `gemini_usage`, unit tests with the model mocked | UI, camera plugin, Cloudinary, saving a recipe, Railway / Stripe / secrets |
| 2 | Web review | "Import from photo" / "Snap a recipe" in the wizard, up to 4 JPEG/PNG/WebP files, prefill of the existing review steps, error and paywall states, `NEXT_PUBLIC_PHOTO_IMPORT_ENABLED` default off | Native camera, HEIC decoder, uploading the photo |
| 3 | Capacitor | `@capacitor/camera` (free, already in the Capacitor 8 line): `pickImages` limited to 4 and `getPhoto` for one snap, JPEG output so the device converts HEIC, camera and photo-library permission strings. Branch on `Capacitor.isNativePlatform()`. Same endpoint | A new model, a new usage field |
| 4 | Rollout | Staging samples against the cost budget, then an operator turns the two flags on. Optional follow-up: "Use this photo" uploads the local file through the existing upload route after save | Changing the pinned model via Railway, storing the extraction upload |

Phase 1 is deliberately the whole server contract (count, cap, model, privacy).
Later PRs only add clients.
