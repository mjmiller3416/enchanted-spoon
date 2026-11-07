# Enchanted Spoon mobile web audit

Date: 2026-11-07. Target: https://enchantedspoon.app (production). No account was signed in, no checkout was opened, and no recipe-import or other paid generation endpoint was called.

## Verdict

**No-go for a broad public push.** This pass only exercised the public marketing site, pricing display, sign-in and sign-up shells, and the redirect that keeps unsigned visitors out of the app.

**Not a clearance of the app Mitchell's household actually uses.** Recipes, search, filters, recipe detail, create/edit/import, meal planning, the shopping list, onboarding, modals, and Settings → Plan & Billing were not rendered. Clerk keys are not available in this environment, and credentials were not invented.

**A small trial of the existing app is reasonable only for people who can already sign in, after one signed-in pass on a phone and a tablet.** Nothing in the public portrait layouts failed hard enough to stop the two households already using it. That is not the same as evidence the app shell is fine on a Galaxy S26 Ultra, a Tab S10 FE, or a Pixel 9 Pro XL.

## What was actually run

Linux cloud VM. Playwright **1.56.1**:

| Engine | Build | What it is |
| --- | --- | --- |
| Chromium | 141.0.7390.37 (Playwright build v1194) | Desktop Chromium with a mobile viewport, DPR, touch flag, and user agent |
| WebKit | 26.0 (Playwright build v2215) | Playwright's WebKit, not iOS and not Safari on a phone |
| Firefox | 142.0.1 (Playwright build v1495) | Firefox with viewport and user agent only |

No physical phone or tablet was used. Samsung One UI, Android 17, and iOS were not booted. Capacitor was not launched. The hosted site is what the native shell loads (`capacitor.config.ts` server URL `https://enchantedspoon.app`).

Playwright 1.56.1 does **not** include presets named Galaxy S26 Ultra, Pixel 9 Pro XL, Pixel 9, or Galaxy Tab S10 FE. Those contexts below are labeled approximations. Firefox rejects `isMobile`; `deviceScaleFactor` and `hasTouch` were omitted there. Observed Firefox `devicePixelRatio` was 1 and `maxTouchPoints` was 0. WebKit kept the preset DPR but still reported `maxTouchPoints` 0.

### Approximations (not presets)

| Name | CSS viewport | DPR | Why this number |
| --- | --- | --- | --- |
| Pixel 9 Pro XL | 448×997 portrait, 997×448 landscape | 3 | Google's panel is 1344×2992, 6.8 in. phone-simulator.com, 1440px.com, and screenmetriclab.com agree on 448×997 at DPR 3. screenmetriclab.com says the CSS profile was not measured on a device. User agent is constructed (`Android 17; Pixel 9 Pro XL`, Chrome/141). |
| Galaxy S26 Ultra, default display size | 384×832, landscape 832×384 | 2.8125 | doesitfit.lol (Sep 2026) estimates this and says it was not measured in a browser. Physical figure cited there is 1440×3120. |
| Galaxy S26 Ultra, smaller display size | 412×892 | 2.625 | doesitfit.lol's "Display size: smaller". screensize.io instead calls 412×891 at DPR 2.625 the default. webmobilefirst.com's 1648×3564 panel was not used; it conflicts with the other two. |
| Galaxy Tab S10 FE | 960×1536, landscape 1536×960 | 1.5 | Samsung's developer skin and GSMArena: 10.9 in, 1440×2304. screensize.io derives 960×1536 at DPR 1.5. Not read from `window.devicePixelRatio` on a tablet. User agent has no `Mobile` token. |
| Custom 800×1280 | 800×1280 | 2 | Requested width bucket. Not a device. |

Genuine presets used as-is: iPhone SE (320×568), iPhone SE landscape, iPhone SE (3rd gen) (375×667), Galaxy S8 (360×740), Galaxy S24 (360×780) and landscape, iPhone 13 (390×664) and landscape, iPhone 14 Pro Max (430×740), Pixel 7 (412×839) and landscape, Galaxy Tab S9 (640×1024) and landscape (1024×640), iPad Mini (768×1024) and landscape, iPad (gen 7) (810×1080).

## Coverage

Core flows, each engine that ran them: landing reflow, header, scroll, tap Get started → `/sign-up`, pricing text and "Start with Pro" → `/sign-up` (no Stripe), privacy and terms reflow, sign-in (type `a`, do not submit, Tab to the email field, do not click Google), sign-up fields not submitted, auth gate, half-width reflow proxy on `/privacy`.

Full flows (Chromium Pixel 7 was cut short by a bad assertion; Firefox Pixel 7 and WebKit iPhone 13 finished them): delete-account display without activating mailto, What's New, Ctrl+Plus zoom.

| Check | Result |
| --- | --- |
| Landing, no document horizontal scroll | Pass, 30/30 contexts |
| Header inside the viewport | Pass, 30/30 |
| Get started → `/sign-up` | Pass, 30/30 |
| Pricing shows $0, $6.99, $49.99, no checkout navigation | Pass, 19/19 core contexts |
| Start with Pro → `/sign-up`, not Stripe | Pass, 19/19 |
| Privacy and terms reflow | Pass, 19/19 |
| Half-width reflow proxy (stand-in for 200% zoom) | Pass, 18/18 that reached it |
| Sign-up email + password field, not submitted | Pass, 19/19 |
| Tab reaches the email field | Pass, 19/19 |
| Invalid `a` stays on `/sign-in` (browser email validation) | Pass, 19/19 |
| Google button visible, not clicked | Pass, 19/19 |
| `/dashboard`, `/recipes`, `/recipes/1`, `/meal-planner`, `/shopping-list`, `/settings` redirect to `/sign-in` | Pass, 19/19 |
| Authenticated app UI | **Blocked, 19/19** |
| Ctrl+Plus browser zoom | **Blocked.** Headless Chromium, WebKit, and Firefox left `visualViewport.scale` at 1 |
| Pinch zoom, OS keyboard, voice input | Not run |
| Local seeded app | Not run. `CLERK_SECRET_KEY` and `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` are unset. `AUTH_DISABLED` would only mock the API; it would not paint the signed-in UI, and it was not used |

Light theme was forced on one Pixel 7 Chromium context (`localStorage` `enchanted-spoon-theme` = `"light"` plus `colorScheme: "light"`). Pricing and sign-in rendered in light colors. A follow-up wait-for-`h1` capture of the landing page did too (`background-color: rgb(248, 249, 250)`). The first landing screenshot in that context was blank because it was taken before the document had a header or `h1`. Same race on the first Galaxy S26 Ultra 384×832 shot. A second capture at 384×832, after `h1` was visible, showed the landing page with overflow 0.

## Issues

### 1. Short landscape sign-in hides the email field until you scroll

Priority: **P2**. Not a portrait-phone blocker.

`frontend/src/app/(auth)/layout.tsx` centers the card with `min-h-screen flex items-center justify-center`. On the genuine Playwright **iPhone SE landscape** preset (568×320, DPR 2, WebKit user agent, Chromium engine for this follow-up):

- At scroll 0 the email box was y=313, bottom=353, viewport height 320. The label is on screen; the input is clipped.
- `scrollHeight` was 494, so the page does scroll. `scrollIntoView` moved the field to y=140.

Portrait Pixel 7 (412×839) kept the email, Google button, and Continue on screen, including after the audit's height shrink, and the field showed the unsent character `a`. A later probe on portrait iPhone SE at the real 568px height also kept the field on screen (y=376, bottom=416). Shrinking that viewport and then focusing scrolled the field into view (`scrollY` 245). The audit's six "keyboard inset" failures were harsher than a real IME: the field was already focused, then the layout height was cut by 320px, and a second `focus()` did not scroll. Treat those six rows as a test limitation. The landscape preset measurement is the product issue.

### 2. Signed-out unknown URLs go to sign-in, not the not-found page

Priority: **P3**.

`GET /not-a-real-mobile-audit-route` returns **307** to `/sign-in?redirect_url=...` with `x-clerk-auth-status: signed-out`. The public `not-found.tsx` ("Page not found", including a Browse recipes link to `/recipes`) is not what a signed-out visitor sees. The first script run marked this as a failure because it expected an `h1`. That was a bad assertion. WebKit rerun records it as a warning. The page that loads is the normal sign-in form.

### 3. Header tap targets are 40px, logo is 32px

Priority: **note, not a defect against WCAG 2.2 AA 2.5.8 (24px).** No on-screen button or input was under 24px. Sign in / Get started measured 40px tall (`h-10`). The logo link measured 32×32. Below the `sm` breakpoint (640px) the wordmark and the header Pricing link are `hidden sm:inline-flex`. Pricing remains in the footer. That is how the component is written.

### Not filed

- Document `scrollWidth` never exceeded the viewport by more than 2px on the pages measured. Some below-the-fold carousel slides report a box wider than the viewport (`translate` / `bg-primary` progress) while the document itself does not scroll sideways. Clipped track, not page overflow.
- WebKit logged "access control checks" for `clerk.enchantedspoon.app` and for a few same-origin `/pricing?_rsc=` prefetches. The sign-in form still appeared and the flows above still passed. Chromium and Firefox did not record uncaught page errors. This is Playwright WebKit 26 on Linux, not an iOS Safari result.
- Safe-area: one early CDP `Emulation.setSafeAreaInsetsOverride` (top 47, bottom 34) computed `env(safe-area-inset-top)` as 47px while the marketing header stayed at y=0. Repeats in the matrix computed an empty padding, so it is **not** a stable reproduced bug. Source fact, unverified on device: `viewportFit: "cover"` is set, the marketing header and `TopNav` do not pad `safe-area-inset-top`, and `MobileBottomNav` does pad the bottom inset. Normal mobile Chrome often reports a 0 inset because the browser chrome already clears the status bar.

## Authenticated coverage gap (for a signed-in browser)

Do this on one phone and one tablet that are actually signed in. Do not delete recipes, do not change production settings, do not start checkout, and do not spend an AI import or generation unless you mean to.

1. Existing account: `/dashboard` onboarding tour and starter content, if it still shows.
2. New account, if you have a disposable one: same tour, then confirm it does not appear again.
3. `/recipes`: search, filters, open a recipe, long directions.
4. Create and edit a recipe you can throw away. URL import only if a paid call is acceptable. The wizard method "Import File" is present and **disabled** (`isAvailable: false`).
5. `/meal-planner`: add and remove using that disposable recipe.
6. `/shopping-list`: check, add, the bottom-nav badge.
7. Bottom nav More sheet, one dialog, one form.
8. Settings → Plan & Billing: read it. Do not press checkout.
9. Rotate to landscape on the real phone, especially sign-in if you can open it from a signed-out window.

## Photo → recipe (assessment only, not built)

**This feature does not exist.** What exists:

- **URL import** (`RecipeImportService.import_from_url`): fetch HTML, recipe-scrapers / schema.org, otherwise Gemini text over page text. TikTok and Instagram use the caption or pasted text. The prompt says to convert faithfully and not invent ingredients or steps; it can return `no_recipe_found`. The source photo is downloaded (10 MB cap) as the recipe image, not as something the model reads. Quota: Pro 50 imports / month (`usage_limits.py`).
- **Wizard review already exists.** Import and AI generate call `populateFromGeneration`, switch the method to manual, land on step 2, and toast "review and edit below." Steps 3 and 4 are ingredients and directions before save (`IngredientsStep`, `DirectionsNotesStep`).
- **Manual photo upload** (`ImageUploadCard`, `accept="image/*"`, 15 MB client and `upload.py`) attaches a picture to a recipe that is already structured. It is stored in Cloudinary under the recipe's `image_key`. It is not OCR.
- **Image generation** writes a food photo from the recipe name. The only image bytes sent into Gemini are a generated PNG so a banner can be cropped from it (`generate_banner_from_reference`). That is image output, not reading a cookbook page.
- **Import File** on the method picker is a disabled placeholder ("Upload a recipe file"), not a camera flow.

Smallest useful scope: one new wizard method, "Photo", beside the disabled file card. One authenticated endpoint accepts a single image, sends it to a vision-capable model with the **same JSON contract and the same do-not-invent / `no_recipe_found` rules** as URL import, and returns into `populateFromGeneration`. The person fixes quantities, units, and steps before save. Keep the page photo as an optional attachment through the existing upload path, in the account's private Cloudinary folder, not as a claim that the model understood every word.

Leave these out of that first slice: multi-page and multi-recipe detection, auto-save, inferred ingredients, allergen or diet guarantees, HEIC transcoding (the file input is `image/*` and the server only checks `content-type` starts with `image/`; there is no EXIF rotation step in app code), and copyrighted cookbook pages stored as if they were the user's own text. Handwriting that is illegible should come back as blanks or `no_recipe_found`, not guesses.

Do this **after** the signed-in mobile pass of the current wizard, not before. The photo flow sits on screens this audit could not open. It is not required for a small trial of the app as it is, and it should not jump ahead of that trial.

## How to reproduce

```bash
cd qa/mobile-web-audit
npm install
npx playwright install chromium webkit firefox
# Linux libraries if the browsers refuse to launch:
# sudo npx playwright install-deps
AUDIT_OUT=/tmp/enchanted-spoon-mobile-audit npm run audit
# WebKit only, after the wheel-scroll fix:
AUDIT_ENGINES=webkit AUDIT_OUT=/tmp/enchanted-spoon-mobile-audit-webkit npm run audit
```

Raw machine output from this run is not committed (screenshots and `results.json` are large). The script writes `results.json` and `summary.md` under `AUDIT_OUT`.
