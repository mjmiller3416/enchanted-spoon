# Enchanted Spoon UI — build conventions

## Canvas & theme
Dark mode is the DEFAULT (`:root` holds the dark palette); light mode exists only when the `light` class is on the root `<html>` element. No provider is required — components work standalone (`Tooltip` embeds its own provider). Give every screen the app canvas: `bg-background text-foreground`. Mount `<Toaster />` once if you use toasts.

## Styling idiom: semantic Tailwind tokens ONLY
Never use raw palette classes (`text-gray-500`, `bg-slate-800`) or arbitrary values (`h-[38px]`) — always the semantic tokens and the standard scale (`h-10`, `gap-4`).

- Surfaces: `bg-background` (canvas) · `bg-background-subtle` · `bg-background-intense` (modal-deep) · `bg-sidebar` · `bg-elevated` / `bg-card` (cards) · `bg-popover` · `bg-muted` · `bg-accent` · `bg-hover` · `bg-input`
- Text: `text-foreground` · `text-foreground-subtle` · `text-muted-foreground` · `text-foreground-disabled`
- Brand: purple primary `bg-primary text-primary-foreground` (hover `bg-primary-hover`, tinted `bg-primary-surface` + `text-primary-on-surface`, border `border-primary-muted`); teal secondary mirrors it (`bg-secondary`, `bg-secondary-surface`, `text-secondary-on-surface`)
- Status: `bg-success` `bg-warning` `bg-error` `bg-destructive text-destructive-foreground` `bg-info`; tinted `bg-success-surface` + `border-success-surface-border`
- Charts/stat accents: `bg-chart-1`…`bg-chart-6`, `text-chart-1`…`text-chart-6` (purple, teal, amber, pink, green, indigo)
- Borders: `border-border` (default) · `border-border-subtle` · `border-border-strong`; focus ring `ring-ring`
- Depth (the "weight system"): `shadow-raised` → `shadow-elevated` → `shadow-floating`; pressed `shadow-inset-sm`/`shadow-inset-md`; glow `shadow-glow-primary`/`shadow-glow-secondary`; composed surfaces `surface-base|raised|elevated|floating`
- Motion: hover/press composites `pressable` `liftable` `interactive` `interactive-subtle` `bouncy`; buttons `button-weighted` `button-bouncy` `button-modal-cancel`; easing `ease-physical` `ease-bounce` `ease-snap`; entrances `animate-fade-in` `animate-slide-up` `animate-scale-in`
- Typography roles: `text-page-title` `text-section-header` `text-card-title` `text-body` `text-meta` `text-ui`
- Layout helper: `widget-column` for columns holding shadowed cards (never put `overflow-hidden` on a parent of a shadowed card — it clips the shadow); `image-zoom-wrapper` for hover-zoom images

## Component rules
- Use the real components — never fake a card/button/badge with styled divs. `Card` is `flex flex-col` by default: any horizontal row directly inside needs explicit `flex-row`.
- Icons: `lucide-react` with `strokeWidth={1.5}`. Icon-only `Button size="icon"` MUST have `aria-label`.
- Async buttons show `<Button disabled><Loader2 className="animate-spin" /> Saving…</Button>`.
- Overlays: `Select`/`DropdownMenu` content renders inline (no portal) — `defaultOpen` works for static comps. `MultiSelect` and `ChangelogPopover` hold open-state internally (no `open` prop).
- `QuantityInput` requires `onChange`; static `value` renders formatted unicode fractions.
- Domain pieces to reach for: `StatCard` (dashboard tiles, `colorClass` purple|pink|teal|amber|green|indigo), `RecipeBadge`/`RecipeBadgeGroup`, `RecipeImage` (placeholder fallback built in), `PageHeader` + `PageHeaderTitle`/`PageHeaderActions`, `FilterBar`/`FilterPillGroup`, `IconButton`, `NumberStepper`, `Logo` (mark only — inherits `currentColor`; compose wordmark text yourself).

## Where the truth lives
Read `styles.css`'s import closure — `_ds_bundle.css` holds every compiled token and utility (search a class there before inventing one), `fonts/fonts.css` ships Geist/Geist Mono. Per-component API: `components/<group>/<Name>/<Name>.d.ts`; usage: `<Name>.prompt.md`.

## Idiomatic example
```tsx
import { PageHeader, PageHeaderTitle, PageHeaderActions, StatCard, Button } from "recipe-app";
import { BookOpen, Heart, Plus } from "lucide-react";

export function Dashboard() {
  return (
    <div className="bg-background text-foreground min-h-screen p-6 space-y-6">
      <PageHeader>
        <PageHeaderTitle>Dashboard</PageHeaderTitle>
        <PageHeaderActions>
          <Button><Plus strokeWidth={1.5} /> Add Recipe</Button>
        </PageHeaderActions>
      </PageHeader>
      <div className="grid grid-cols-2 gap-4">
        <StatCard icon={BookOpen} value={42} label="Total Recipes" colorClass="purple" />
        <StatCard icon={Heart} value={12} label="Favorites" colorClass="pink" />
      </div>
    </div>
  );
}
```
