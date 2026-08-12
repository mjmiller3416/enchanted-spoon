// ============================================
// CHANGELOG - Edit the markdown below
// ============================================
const CHANGELOG_MD = `
## 2026-08-09 - Improvements
- Groundwork for Pro subscriptions — Stripe checkout, billing portal, and automatic subscription syncing (upgrade flow UI coming soon)
- AI requests now retry automatically on temporary failures instead of hanging
- Monthly AI usage limits to keep costs predictable

## 2026-08-09 - Bug Fixes
- Genie no longer produces empty recipe drafts when generation fails
- Fixed missing-item errors in ingredient and unit settings showing as server errors

## 2026-08-05 - Bug Fixes
- Recipe Browser filters, search, and sort now stay applied when you navigate away and come back — not just when opening a recipe
- Fixed a Shopping List bug where manually added items could land in a duplicate "Other" category instead of joining the existing one
- Genie chat now lets you know if it couldn't put together a full recipe, instead of handing you one with no ingredients or directions
- Fixed Meal Planner scrolling on mobile — swiping over a meal card now scrolls the page instead of getting stuck

## 2026-07-20 - New Features
- External shopping list integration — trusted apps can now push items directly to your Shopping List via a secure API

## 2026-07-14 - New Features
- Redesigned Home — a new today-first view centered on today's planned meal, with your cooking streak now shown in the header and a guided setup flow for first-time users
- Unified Meal Creation — one streamlined flow for building meals, now including recipe roulette for random picks, with a direct path from planning your week to generating your shopping list
- Import Recipe from URL — paste a link to any online recipe in the Recipe Wizard and it fills in automatically
- New Landing Page — a public landing page featuring live app previews instead of static screenshots
- Theme Settings — choose Light, Dark, or System from Settings or the mobile menu, with no more dark-mode flash when the page loads
- Genie on Mobile — a floating assistant button keeps Genie within reach on phones, plus a new "Generate a recipe" shortcut in the Recipe Browser

## 2026-07-14 - Improvements
- Settings cleanup — placeholder sections removed so Settings shows only working options, and the About section now shows the real app version
- Accessibility — better keyboard support in the Meal Planner, reduced-motion support for animations, and improved screen-reader labels
- Refreshed body font for a cleaner reading experience

## 2026-07-14 - Bug Fixes
- AI badges now correctly distinguish AI-generated recipes from AI-generated photos — recipes with only an AI-generated image no longer show as fully AI-generated

## 2026-07-12 - Bug Fixes
- Printed recipes now reliably include the recipe photo — previously the photo could be missing from printouts, especially after regenerating a recipe image

## 2026-06-23 - Improvements
- Faster AI features — AI recipe generation and nutrition estimation now respond more quickly
- Genie chat is now more responsive while generating replies
- Recipe Wizard — reduced input lag for a snappier typing experience when adding ingredients

## 2026-06-18 - Improvements
- Recipe total time is now automatically calculated from prep and cook times
- Improved AI image generation with enhanced prompts for more accurate recipe photos

## 2026-06-17 - New Features
- Recipe Wizard — create and edit recipes with a new step-by-step guided workflow featuring method selection, ingredient management, directions, and nutrition facts
- AI Recipe Generation — ask Genie to generate a complete recipe draft that auto-populates the Recipe Wizard, tailored to your existing recipes and preferences
- Nutrition Facts — recipes now display detailed nutrition information with an option to include it in printed recipes
- Quick Meal Creation — create meals from anywhere in the app using the new global creation overlay

## 2026-06-17 - Bug Fixes
- Fixed Genie responses occasionally failing after AI service updates
- Improved recipe form accessibility and design consistency

## 2026-03-24 - Improvements
- Genie Assistant Visibility — the assistant now intelligently manages its visibility based on screen size and user interaction for a cleaner browsing experience

## 2026-03-24 - New Features
- Mobile Bottom Nav "More" Menu — access additional pages and features from a new expandable menu in the mobile navigation bar
- Mobile Assistant UX — improved Genie chat experience on mobile devices

## 2026-02-22 - New Features
- Meal Planner Drag Overlay — Long-press on meal cards in the planner to enter drag-and-drop mode, allowing you to easily rearrange your weekly menu with a visual overlay showing potential drop targets.
- Dashboard Meal Carousel — Browse your upcoming meals in a swipeable carousel with recipe images and details at a glance.
- Recipe Browser Filter/Sort (Redesign) — Redesigned filter and sort controls that stay visible as you scroll through recipes.
- Customizable Ingredient Units & Categories — user-defined units and ingredient categories, accessible from Settings → Shopping List / Recipe Preferences, allowing you to tailor the shopping list to your preferences and pantry organization.
- Customizable Recipe Categories — create your own recipe categories and assign them to recipes for better organization and filtering in the Recipe Browser.
- AI-Generated Recipe Badges — recipe cards now display AI-generated badges when generated by Genie.
- Selective Image Generation — choose between reference and banner image generation.
- Top-bar Navigation — replaces Sidebar, new layout with quick access to key pages and features.
- Top-bar Notifications (Redesign) — new bell icon in the top right corner for changelog updates and other important alerts.
- Top-bar Quick Add Button — new "+" button in the top right corner for quick access to creating meals, recipes, and shopping list items (coming soon!) from anywhere in the app.

## 2026-02-22 - Bug Fixes
- Shopping List Category Mismatch — eliminated mismatched categories for certain ingredients.
- Feedback Form — fixed issue where feedback form could not be submitted due to missing authentication token.
- Multi-Word Ingredient Autocomplete — autocomplete now works with multi-word search terms.
- Recipe Filter State Persistence — fixed an issue where active filters in the Recipe Browser would reset when navigating away and back to the page.
- Recipe Form Input Lag — typing in the recipe form now feels faster and more responsive.

## 2026-02-22 - Improvements
- Settings Autosave — all settings changes now save instantly without needing to click a "Save" button, with a quick confirmation when changes are saved.
- Page Layouts Updated — improved titles, descriptions, and header content.

## 2026-02-01 - New Features
- Custom Recipe Groups — organize your recipes into collections like "Weeknight Dinners" or "Holiday Favorites" and filter by group in the Recipe Browser
- Meal Planner — now auto-selects the next meal after completing one — no need to manually pick the next meal in your queue

## 2026-02-01 - Bug Fixes
- Fixed cooking streak not updating correctly when clearing completed meals from the planner

## 2026-01-30 - Bug Fixes
- Fixed duplicate badge display in meal planner selection screen — recipe cards no longer show redundant Main/Side badges
- Improved selection UX in meal planner — checkmark now appears in top-left corner without shifting the favorite button
- Fixed dashboard stats to properly exclude cleared and completed meals from the "Meals Planned" count
- Auto-populate meal name with recipe name when creating meals from the planner
- Fixed cooking streak widget to properly update when clearing completed meals from the planner

## 2026-01-29 - Bug Fixes
- Fixed authentication for AI features — image generation and Genie now properly authenticate requests to prevent unauthorized access
- Resolved infinite loading issue with AI suggestions in the Meal Planner — suggestions now load correctly every time
- Fixed meal name preservation when editing meals in the planner — names no longer revert to default values
- Your shopping lists, meal plans, and recipes are now fully private to your account

## 2026-01-24 - New Features
- Full Data Backup & Restore — create complete JSON backups of all your data (recipes, meals, planner entries, shopping lists, and settings) from Settings → Data Management
- Configure your default recipe sort order in Settings → Recipe Preferences — choose between A-Z, Most Recent, or Cook Time
- New Meal Planning settings section — set your default servings (1-12) and choose whether your week starts on Sunday or Monday
- New Shopping List settings section — choose when checked items are cleared (Manual, On Refresh, or Daily)

## 2026-01-24 - Improvements
- Quick Add widget now suggests ingredients as you type, matching the autocomplete behavior from the recipe editor — selecting an ingredient auto-fills the category
- Shopping list categories now display custom icons instead of generic emojis — each category (Produce, Meat, Dairy, Spices, etc.) has its own distinct icon
- Recipe icons are now smarter with priority-based matching — specific keywords like "salmon" match before generic ones like "fish" for more accurate icons
- Expanded recipe icon coverage with 25+ new food keywords mapped to icons, reducing emoji fallbacks

## 2026-01-21 - Improvements
- Genie now prioritizes your saved recipes when making suggestions

## 2026-01-21 - Bug Fixes
- Fixed dropdown menus appearing incorrectly on some pages

## 2026-01-20 - New Features
- Drag-and-drop reordering of meals in the Meal Planner sidebar

## 2026-01-20 - Improvements
- AI image generation now shows a progress bar so you can see each step as your recipe image is created
- Meals in the planner are now automatically saved when you add them — no extra steps needed

## 2026-01-20 - Bug Fixes
- Fixed issue where Genie could create duplicate recipes when generating suggestions

## 2026-01-19 - Improvements
- Genie now provides 6-10 creative recipe ideas immediately when you ask for suggestions, instead of asking questions first
- Improved chat experience with smooth animations and scroll indicators

## 2026-01-18 - Improvements
- Recipe pages now display beautiful banner images at the top for a more immersive cooking experience

## 2026-01-17 - Bug Fixes
- Fixed issue with printing recipes. Content now stays together on the same page.

## 2026-01-14 - New Features
- Add recipe specific AI suggestions to the Meal Planner
- Quick Add feature for adding shopping list items directly from the Dashboard

## 2026-01-13 - New Features
- Shopping list toggle now has three modes: include all ingredients, include only produce, or exclude entirely — click the cart icon on meal cards to cycle through options
- Hover over the shopping cart icon to see a tooltip explaining the current mode

## 2026-01-10 - New Features
- Genie Assistant can now create recipes when prompted - just ask it to "create a recipe for ..."

## 2026-01-10 - Improvements
- Genie now knows about your saved meals, meal plan, and shopping list.
- Suggestions from the Genie are now more relevant, using your existing meals, shopping list, and preferences to tailor its responses.

## 2026-01-10 - Bug Fixes
- Print layout now keeps the recipe image and content together on the same page
- Flagged shopping items now stay flagged when you make changes to your meal plan
- Chef's Tips on the Dashboard now shows a wider variety of cooking tips instead of repeating the same ones

## 2026-01-04 - Bug Fixes
- Fixed issue with adding meals to the planner from the Recipe Browser

## 2026-01-04 - Improvements
- Added multi-select filters to the Meal Planner for easier meal searching and filtering

## 2026-01-04 - New Features
- Revamped Meal Planner UI 

## 2026-01-02 - Improvements
- Genie now saves your chat history between sessions
- Genie responses are now faster
- Genie chat now opens in a popup window

## 2026-01-02 - New Features
- Recipe Roulette: Randomly suggests recipes based on your existing recipes, meal planner, or favorites

## 2026-01-01 - Bug Fixes
- Fixed issue where shopping list did not update correctly after removing all meals from the planner
- Fixed various bugs related to the Shopping List and Meal Planner pages

## 2026-01-01 - Improvements
- Added "Create Meal" button to Meal Planner sidebar - quick access to meal creation
- "Add Meal" button in Meal Planner now opens the "Saved Meals" tab by default for faster access

## 2026-01-01 - New Features
- Add flags to shopping list items to mark them as important or "don't forget" - flagged items appear at the top of their category and have a visual indicator
- AI-powered Genie chatbot on the Dashboard — get cooking tips, recipe ideas, and meal suggestions instantly

## 2025-12-31 - Improvements
- Improved responsiveness of the sidebar on mobile devices

## 2025-12-30 - New Features
- Exclude individual meals from your shopping list — click the cart icon on any meal card in the planner sidebar (green = included, red = excluded)

## 2025-12-30 - Improvements
- Shopping list page now loads faster

## 2025-12-29 - New Features
- Track your cooking streak on the Dashboard — see consecutive days cooked and this week's activity at a glance
- New Dashboard homepage with at-a-glance stats, meal queue, shopping list preview, and AI-powered Chef's Tips
- Manually added shopping list items can now be assigned to specific categories (Produce, Dairy, Meat, etc.) instead of always appearing in "Other"
- Add items manually to your shopping list with the new inline form — perfect for pantry staples and non-recipe items
- Click your profile avatar in the sidebar to access Settings

## 2025-12-29 - Improvements
- Shopping list categories now auto-collapse when all items are collected
- Collapsed and expanded category states persist between page visits
- New "Hide collected" toggle replaces "Clear collected" — filter your view without losing data
- Recipe ingredients now display in a logical order with Meat and Seafood first, followed by produce, dairy, and pantry items
- Sidebar now fits better on smaller screens

## 2025-12-29 - Bug Fixes
- Meal Queue on the dashboard now displays meals correctly
- Shopping list categories now auto-expand when new items are added to a completed category
- Shopping list badge in sidebar now updates in real-time when adding, removing, or completing meals in the planner
- Dashboard widgets (Meal Queue, Shopping List, Cooking Streak) now refresh instantly when planner changes — no page reload needed
- Cooking streak widget now marks the correct day when completing meals
- Shopping list properly clears recipe items when all meals are removed from the planner
- "Mac Salad" now correctly appears in the Deli section of the shopping list

## 2025-12-28 - New Features
- Quickly add saved meals to your planner from the new "Saved Meals" tab — search by name or filter by favorites
- Configure custom unit conversions for shopping list items in Settings → Shopping List (e.g., convert 51 Tbs of butter to 7 sticks)

## 2025-12-28 - New Features
- Favorite meals directly from the meal planner with the new Favorite button — favorited meals show a heart indicator in the weekly menu
- Customize which quick filters appear in the Recipe Browser from Settings → Recipe Preferences (choose up to 5)
- Customize the AI image generation prompt in Settings → AI Features with syntax highlighting for the {recipe_name} placeholder
- New "New" filter in Meal Planner lets you quickly find recipes added in the last 7 days
- Filter shopping list by recipe using the new sidebar that shows which recipes contribute each ingredient
- Hover over shopping list items to see a breakdown of quantities by recipe

## 2025-12-28 - Bug Fixes
- "Favorites" and "New" quick filter pills in the Recipe Browser now work correctly
- Fixed meal cards in the create/edit meal dialog to display at a consistent size
- Weekly menu in Meal Planner now scrolls properly when there are many items
- Shopping list items now uncheck automatically when their quantity increases from adding new recipes
- Meal planner now auto-selects the first uncompleted meal when you open the page
- Removed duplicate "Pico De Gallo" ingredient that appeared in wrong category
- Ingredient units like "Tbs" now display with proper capitalization on recipe pages
- Fixed loading issues on the Recipes page

## 2025-12-28 - Improvements
- Shopping list now intelligently combines ingredients by unit type — quantities in the same dimension (cups + tbsp, lbs + oz) are merged, while incompatible units (lbs vs cups) appear as separate items
- Print recipes with customizable options — choose to include or exclude the image, chef's notes, and cooking time to fit more content on a single page
- Ingredient quantities now accept leading decimals like .5 or .25 (no need to type 0.5)
- Clicking "Add Ingredient" now automatically focuses the new ingredient name field
- Active filter pills now stay on a single row with horizontal scrolling instead of wrapping
- Shopping list stats now display in a more logical order: Remaining → Collected → Total

## 2025-12-27 - Improvements
- Shopping list now shows quantities before item names for easier scanning while shopping
- Shopping list quantities now display as fractions (½, ¼) instead of decimals
- Side dish cards now enlarge slightly when you hover over them in the meal planner
- Improved sidebar navigation

## 2025-12-27 - Bug Fixes
- Quick filter chips no longer add duplicate entries to the active filters display
- Fixed pages jumping when opening dropdowns and dialogs
- The "Favorites Only" filter in Recipe Browser now works correctly
- Card shadows now display with properly rounded corners

## 2025-12-27 - New Features
- Quickly access recently viewed recipes from the sidebar

## 2025-12-27 - Improvements
- Drag-and-drop reordering of ingredients when adding or editing recipes
- Fixed ingredient autocomplete for multi-word ingredients like 'olive oil'
- Removed duplicate 'Ranch Seasoning' ingredient from database
`;

// ============================================
// Parser & Helpers
// ============================================
import { Star, Bug, Zap, Sparkles, type LucideIcon } from "lucide-react";

export interface ChangelogEntry {
  version: string;
  date: string;
  title: string;
  changes: string[];
}

export interface ChangelogItem {
  change: string;
  category: string;
  rawDate: string;
  date: string;
  globalIndex: number;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function parseChangelog(markdown: string): ChangelogEntry[] {
  const entries: ChangelogEntry[] = [];
  const sections = markdown.split(/^## /gm).filter(Boolean);

  for (const section of sections) {
    const lines = section.trim().split("\n");
    const headerMatch = lines[0].match(/^(\d{4}-\d{2}-\d{2})\s*-\s*(.+)$/);
    if (!headerMatch) continue;

    const [, version, title] = headerMatch;
    const changes = lines
      .slice(1)
      .filter((line) => line.startsWith("- "))
      .map((line) => line.slice(2).trim());

    entries.push({
      version,
      date: formatDate(version),
      title: title.trim(),
      changes,
    });
  }

  return entries;
}

export const CHANGELOG_ENTRIES = parseChangelog(CHANGELOG_MD);

// Calculate total number of individual change items
export const CHANGELOG_TOTAL_ITEMS = CHANGELOG_ENTRIES.reduce(
  (sum, entry) => sum + entry.changes.length,
  0
);

// Helper to get the cumulative item count up to (but not including) a given entry
export function getItemCountBeforeEntry(entryIndex: number): number {
  return CHANGELOG_ENTRIES.slice(0, entryIndex).reduce(
    (sum, entry) => sum + entry.changes.length,
    0
  );
}

// Flatten all entries into individual change items (newest first)
export function getFlattenedChanges(limit?: number): ChangelogItem[] {
  const items: ChangelogItem[] = [];
  let globalIndex = 0;

  for (const entry of CHANGELOG_ENTRIES) {
    for (const change of entry.changes) {
      items.push({
        change,
        category: entry.title,
        rawDate: entry.version,
        date: entry.date,
        globalIndex,
      });
      globalIndex++;
      if (limit && items.length >= limit) return items;
    }
  }

  return items;
}

// Parse "Title — description" pattern from change text
export function parseChangeText(text: string): { title: string; description: string | null } {
  const separatorIndex = text.indexOf("\u2014");
  if (separatorIndex === -1) {
    return { title: text, description: null };
  }
  return {
    title: text.slice(0, separatorIndex).trim(),
    description: text.slice(separatorIndex + 1).trim(),
  };
}

// Get icon component based on changelog category
export function getCategoryIcon(title: string): LucideIcon {
  if (title.toLowerCase().includes("feature")) return Star;
  if (title.toLowerCase().includes("fix")) return Bug;
  if (title.toLowerCase().includes("improvement")) return Zap;
  return Sparkles;
}

// Get accent color class based on changelog category
export function getCategoryColor(title: string): string {
  if (title.toLowerCase().includes("feature")) return "text-primary";
  if (title.toLowerCase().includes("fix")) return "text-secondary";
  if (title.toLowerCase().includes("improvement")) return "text-muted-foreground";
  return "text-muted-foreground";
}
