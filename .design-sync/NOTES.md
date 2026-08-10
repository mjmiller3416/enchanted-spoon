# design-sync notes — Whiskful (frontend/)

## Repo shape
- This is an APP repo, not a packaged library: no dist/, no shipped .d.ts. The sync bundles a
  curated barrel `frontend/design-sync.entry.tsx` (cfg.entry) so app-coupled components stay out.
- Components excluded on purpose (crash without the Next.js runtime — router/Clerk/React Query at
  render time): RecipeCard, RecipeBrowserView, TopNav, MobileBottomNav, AppLayout,
  ConditionalAppLayout, SafeLink, FeedbackDialog, RecentRecipeChip, IngredientAutocomplete,
  QuickAddForm, all assistant/ and auth/ components. Revisit RecipeCard if a router-context shim
  ever becomes viable — it's the app's hallmark visual.
- `pkg` is "recipe-app" (frontend/package.json name); repo-root package.json is NAMELESS — don't
  put the barrel outside frontend/ or PKG_DIR resolution walks to the wrong place.

## Styling pipeline
- Tailwind v4: no static stylesheet exists. `cfg.buildCmd` compiles
  `.design-sync/tailwind-input.css` (wraps `frontend/src/app/globals.css`) →
  `frontend/.ds-tailwind.css` (gitignored) = cfg.cssEntry. RE-RUN buildCmd before every
  package-build if sources OR previews changed.
- cssEntry is package-bounded: a path outside frontend/ gets skipped with a `!` log line — keep
  the compiled css inside frontend/.
- The tailwind-input wrapper adds `@source "./previews"` so utility classes used ONLY in authored
  previews (.design-sync/previews/) get compiled — Tailwind's auto-detection scans cwd (frontend/)
  and would miss them. Subagents can't recompile CSS (shared file) — previews should stick to
  app-used utility classes; orchestrator recompiles at wave folds.
- Tailwind CLI installed in .ds-sync (v4.3.x) vs app's tailwindcss 4.1.x — compiled output was
  compatible; if a future version skews, pin @tailwindcss/cli to the app's minor.
- The app is DARK by default (`:root` = dark, `:root.light` = light). Preview card html hardcodes
  a white body — every authored preview cell wraps content in `bg-background text-foreground p-6
  rounded-xl` to show the real canvas. All previews render dark mode only (`.light` needs the
  class on <html>, unreachable from a cell).

## Fonts
- Geist / Geist Mono come from next/font at runtime — harvested the woff2s + @font-face from
  `frontend/.next/dev/static/` into `.design-sync/fonts/geist.css` (cfg.extraFonts). If the .next
  cache is wiped, any `next dev`/`next build` regenerates it.
- The extraFonts parser ships @font-face rules only — the `--font-geist-sans`/`--font-geist-mono`
  var definitions live in `.design-sync/tailwind-input.css` (`:root` block) so they reach the
  compiled css. Local(Arial) fallback faces are dropped by the parser; the vars reference generic
  fallbacks instead ("Geist", ui-sans-serif, ...).
- Body text in this app is Arial/Helvetica BY DESIGN (globals.css body rule); Geist applies where
  `font-sans`/`font-mono` utilities are used. Don't "fix" Arial-looking body text.

## Verify/capture environment
- No playwright browsers cached; system Chrome is used via
  `DS_CHROMIUM_PATH="C:/Program Files/Google/Chrome/Application/chrome.exe"` for
  package-validate.mjs and package-capture.mjs. playwright npm module lives in .ds-sync
  (installed with PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1).
- Build-log line `exported PascalCase symbols: 0` is expected (the `export *` barrel isn't
  statically scannable); the real check is validate's `window.MealGenie: 179 exports`.

## Preview-authoring playbook (folded from wave 1)
- Wrap EVERY cell in `bg-background text-foreground p-6 rounded-xl` — ghost/muted components are
  invisible on the white card canvas without it (that's what made ChangelogPopover look "blank").
- Compiled-CSS gaps to avoid in previews (not in .ds-tailwind.css unless the app starts using
  them): `gap-1.5 h-1.5 h-40 h-56 w-3/4 w-1/2 pl-5 min-h-64 gap-10+ justify-evenly` — fraction
  widths are absent entirely; use fixed widths (w-24/w-32/w-48). Grep `frontend/.ds-tailwind.css`
  before using anything unusual; preview-rebuild does NOT re-run the Tailwind buildCmd.
- Open states: Select/DropdownMenu content is INLINE in this DS (portal removed in the wrappers) —
  `defaultOpen` just works; use `modal={false}` on DropdownMenu to avoid scroll-lock.
  Popover/Tooltip/Sheet portal to body but `open`/`defaultOpen` capture fine.
  MultiSelect + ChangelogPopover hold open-state in internal useState (no prop) — mount-effect
  `ref.current?.querySelector("button")?.click()` opens them reliably; durable fix would be adding
  an open prop upstream.
- Radix Dialog/Sheet auto-focus paints a stray focus ring in screenshots —
  `onOpenAutoFocus={(e) => e.preventDefault()}` on the Content.
- Multiple defaultOpen Tooltips in one row collide; space with `justify-around` + alternate side.
- Tooltip embeds its own TooltipProvider — no provider wrapper needed anywhere.
- Data URIs (`data:image/svg+xml` + encodeURIComponent) work for AvatarImage/RecipeImage in
  capture; remote image URLs are CSP-blocked downstream — never use them.
- Card base is `flex flex-col` (also in auto-memory): horizontal rows directly on Card need
  explicit `flex-row`. CardFooter `border-t` activates its `[.border-t]:pt-6` rule.
- QuantityInput requires onChange (pass noop); static `value` renders formatted fractions.

## Upstream component quirks noticed while authoring (not preview bugs)
- NumberStepper `hasError` is visually inert: adds `border-destructive` to an inner Input that has
  `border-0` — no red border renders in the app either. Fix candidate in
  frontend/src/components/ui/numeric-stepper.tsx.
- Toggle `default` vs `lg` sizes differ only by padding (both h-10) — only `sm` reads differently.
- Badge `success` variant is a deliberately quiet `bg-success/20 text-white` pill.
- RecipeBadge doc comments name inverted colors ("category: teal", "mealType: purple") vs the
  rendered theme (--primary purple, --secondary teal) — trust tokens, not comments.

## Known render warns (triaged legitimate)
- (none standing — the first-build RENDER_BLANK/THIN set was resolved by authored previews; the
  GRID_OVERFLOW pair (Pagination, PageHeader) was fixed with cardMode "column" overrides)

## Re-sync risks (what can silently go stale)
- **The @source inline() safelist in tailwind-input.css mirrors the DS vocabulary by hand.** A new
  `@utility` or token added to globals.css will NOT ship until either the app uses it or the
  safelist is extended — check the safelist whenever globals.css changes.
- **The barrel (frontend/design-sync.entry.tsx) and componentSrcMap are curated by hand.** New
  components in src/components/ don't sync until added to both; new APP-COUPLED components must
  NOT be added (check imports for next/navigation, @clerk, @/hooks/api first).
- **MultiSelect + ChangelogPopover open-state previews click the FIRST <button> in a mount effect**
  — a DOM-order change inside those components silently captures the closed state instead. The
  capture diff/grade cycle should catch it, but eyeball those two sheets on re-sync.
- **Geist fonts are committed** (.design-sync/fonts/) so the .next-cache harvest doesn't need to
  be repeated; if the font family list ever changes in layout.tsx, re-harvest from
  frontend/.next/dev/static after a dev run.
- **Tailwind CLI (v4.3.x in .ds-sync) vs app tailwindcss (4.1.x)** — compatible today; if compiled
  output ever looks off, pin @tailwindcss/cli to the app's minor.
- **Partially verified by design:** the 20 floor-card components were render-checked but never
  visually graded (no authored previews). ChangelogPopover preview inlines the app's changelog
  data at compile time — it refreshes on every rebuild, but a very stale bundle shows old entries.
- **Environment assumptions:** system Chrome at `C:/Program Files/Google/Chrome/Application/
  chrome.exe` via DS_CHROMIUM_PATH; converter deps live in .ds-sync (reinstall on fresh clone:
  `npm i esbuild ts-morph @types/react @tailwindcss/cli playwright` with
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1).

## Preview scope (2026-07-12 first sync)
- User chose "Core ~25": authored previews for 32 components (3 solo: Button, Dialog, StatCard;
  29 in wave 1); 20 remain on floor cards: AlertDialog, Collapsible, Command, Form, InputOTP,
  Label, ScrollArea, Separator, Toaster, ToggleGroup, ChangelogDialog, CircularImage,
  FavoriteButton, InlineGroupCreator, RecipeIcon, ScrollToTopButton, ThemeToggle, PageLayout,
  RecipeBannerImage, RecipeFilters — standing offer for incremental authoring on any re-sync.
