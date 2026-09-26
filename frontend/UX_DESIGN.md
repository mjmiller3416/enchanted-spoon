# Shared application patterns

Use the existing semantic tokens in `src/app/globals.css`, shadcn primitives, and the Tailwind spacing scale. The current body font is Geist via `--font-sans`.

- `PageLayout` owns page width and gutters. Avoid another viewport-height minimum inside it; the application shell already owns navigation and mobile bottom padding.
- `PageHeader` wraps titles and actions on narrow screens. Use `text-page-title`, `text-section-header`, and `text-card-title` for their corresponding roles.
- `EditorDialogContent` provides phone/full-screen and desktop/bounded framing. Editors own a fixed header/footer and a scrollable middle region.
- `QueryError` provides recoverable loading failures. Keep empty success distinct from failed loading, and retain healthy sections during partial failure.
- `NumberStepper` owns labels, bounds, intermediate typing, and focus/error presentation; pass form accessibility attributes through to its input.
- `SettingsProvider` owns account settings. Consumers use `useSettings`; do not create another local copy or write settings directly to browser storage.
- Personal data is scoped by account. Theme is device-wide. Query clients and editor state remount when identity changes.
- Shared services and primitives should be extended only for demonstrated needs. Keep recipe reading narrower than the recipe grid and shopping focused on its list.

Validation: run tests, TypeScript, lint, and build, plus rendered keyboard/theme/viewport checks for visual changes. The historical context files live under `.claude/context`; hook descriptions are guidance, not proof that a particular editing tool runs them.

Section navigation uses SectionNav for a compact phone selector and a restrained desktop sidebar. Settings and admin sections are represented by the `section` URL parameter; invalid values fall back to the first section. SectionHeader owns the shared heading/icon/description pattern. Keep user-facing copy focused on account actions rather than naming the authentication implementation.
