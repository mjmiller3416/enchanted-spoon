# Release Notes ("What's new") Generator

Write a release entry for the in-app "What's new" dialog, the top-bar popover
and the public `/whats-new` page. This file is the **single source of the
editorial rules** — `/git deploy` follows it too.

## Arguments (optional)

$ARGUMENTS

## Audience

Everyone who uses the app: beta testers today, the public soon. The public
`/whats-new` page is indexed. Write for a home cook, not for the developer.

## Step 1: Gather the changes

- **Plain-text argument:** use it as the raw material.
- **No argument:** collect what is about to ship:
  ```bash
  git log origin/main..origin/staging --pretty=format:"%s%n%b" --no-merges
  ```
  Squash-merge commits carry useful bullet bodies — read them, not just subjects.

## Step 2: Filter — what makes the cut

Include only changes a user could **see or feel**. Leave out:

- Infrastructure, monitoring, logging, CI, dependency bumps, refactors
- "Groundwork for…" / anything not usable yet
- Private integrations (Tada, Hearth, anything behind `X-API-Key`)
- Admin-only tools
- Security fixes and data-isolation details — never describe a vulnerability
  on a public page. At most "Better reliability throughout the app".
- Billing/usage-limit internals (a user-visible billing screen change is fine)
- Fixes for bugs nobody would have noticed, and data clean-ups ("removed a
  duplicate ingredient")

Use **current feature names**: Home, Menu, Recipes / Recipe Browser,
Recipe Wizard, Shopping List, Genie, Settings. Never "Dashboard", "Meal
Planner", "sidebar". When a feature is renamed, update older entries too.

## Step 3: Shape the release

Releases live in `frontend/src/data/changelog.ts` as typed objects in
`RELEASES` (newest first):

```ts
{
  id: "2026-10-03",                 // release date; 2nd release same day → "2026-10-03b"
  headline: "Notes for your shopping trip",   // one line that sells it, ≤ 60 chars
  highlights: [                     // 1–3 things worth trying
    {
      title: "Shopping List notes",           // feature name, 2–5 words
      body: "Jot down store hours…",          // 1–2 sentences: what + why it helps
      image: {                                // optional, see Step 4
        src: "/whats-new/shopping-notes.webp",
        alt: "The Shopping List with the notes pad open",
      },
      href: "/shopping-list",                 // optional in-app "Try it" target
      cta: "Open Shopping List",              // optional button label
    },
  ],
  improvements: ["…"],              // optional one-liners, shown collapsed
  fixes: ["…"],                     // optional one-liners, shown collapsed
}
```

Rules:

- **One release per deploy.** Never split one day into Features / Fixes /
  Improvements entries — that's what the three fields are for.
- **Highlights** are new features or big visible changes. If a release is all
  fixes, pick the most noticeable one as the highlight.
- **About 8 items total.** Combine related changes; drop the rest.
- One-liners: plain sentences, present tense, no trailing period, no "Fixed…"
  prefix (they already sit under "Fixes"). Describe the result:
  "Favorites stay saved", not "Fixed favorites not saving".
- Use typographic quotes (“ ”) and em dashes (—).
- `href` must be an in-app route (`/dashboard`, `/meal-planner`, `/recipes`,
  `/shopping-list`, `/settings?section=…`).

## Step 4: Screenshot (optional, for headline features)

1. Run the app (see the `verify` skill) and open the feature in dark mode.
2. Capture the relevant region at roughly 16:9, about 1200px wide.
3. Convert to WebP into `frontend/public/whats-new/<feature>.webp`:
   ```bash
   cd frontend && node -e "require('sharp')('in.png').resize({width:1200,withoutEnlargement:true}).webp({quality:80}).toFile('public/whats-new/<feature>.webp')"
   ```
4. Use realistic sample data, never a real person's account details.

## Step 4b: Spotlight (optional, at most one per release)

For a headline feature that lives in a specific spot in the UI, add an
in-app "New" badge. Existing accounts see it for 30 days after the release
until they use the feature; accounts created later never do.

1. Add an id to `SpotlightId` in `frontend/src/data/changelog.ts`
   (e.g. `"shopping-notes" | "recipe-import"`).
2. Set `spotlight: "<id>"` on the highlight.
3. Render `<NewFeatureBadge spotlight="<id>" />` beside the feature's label,
   and call `useSpotlight("<id>").dismiss()` when the user first uses it
   (focus, open, click). Example: `ShoppingNotes.tsx`.

Remove stale ids from `SpotlightId` (and their badges) once they're past
the 30-day window.

## Step 5: Insert, show, confirm

1. Prepend the release object to `RELEASES`.
2. Show the user the release (headline, highlights, lists) and ask
   `Accept? (yes / edit / skip)` before committing.
3. Commit:
   ```bash
   git add frontend/src/data/changelog.ts frontend/public/whats-new
   git commit -m "docs: update release notes for YYYY-MM-DD release

   Co-Authored-By: Claude <Model Name> <noreply@anthropic.com>"
   ```

Users who haven't seen the new release get a dot on the What's new button.
