// ============================================
// RELEASE NOTES — "What's new"
// ============================================
// Newest release first. Written for users, not developers — see the
// editorial rules in .claude/commands/changelog.md before adding entries.
//
// - id: release date (YYYY-MM-DD). Unread tracking compares ids as strings,
//   so a second release on the same day takes a letter suffix (2026-10-03b).
// - headline: one line that sells the release.
// - highlights: 1–3 things worth trying, each optionally with a screenshot
//   (public/whats-new/*.webp) and a "Try it" link into the app.
// - improvements / fixes: short one-liners, shown collapsed.

export interface ReleaseHighlight {
  title: string;
  body: string;
  /** Screenshot under /public/whats-new — 16:9 crops read best */
  image?: { src: string; alt: string };
  /** In-app destination for the "Try it" button */
  href?: string;
  /** Button label (defaults to "Try it") */
  cta?: string;
}

export interface Release {
  id: string;
  headline: string;
  highlights: ReleaseHighlight[];
  improvements?: string[];
  fixes?: string[];
}

export const RELEASES: Release[] = [
  {
    id: "2026-09-30",
    headline: "Notes for your shopping trip",
    highlights: [
      {
        title: "Shopping List notes",
        body: "Jot down store hours, coupons or anything to double-check. Notes save as you type and follow your account, so you can write them at home and read them at the store.",
        image: {
          src: "/whats-new/shopping-notes.webp",
          alt: "The Shopping List with the notes pad open",
        },
        href: "/shopping-list",
        cta: "Open Shopping List",
      },
    ],
  },
  {
    id: "2026-09-26",
    headline: "Meal details at a glance, and a friendlier first visit",
    highlights: [
      {
        title: "Meal details beside your Menu",
        body: "Tap a planned meal to see its sides, cook times and Genie's suggestions in a panel next to your Menu — no page change needed.",
        image: {
          src: "/whats-new/menu-meal-details.webp",
          alt: "The Menu with a meal's details open in a side panel",
        },
        href: "/meal-planner",
        cta: "Open Menu",
      },
      {
        title: "A one-minute tour",
        body: "A quick walkthrough of Home, Recipes, Menu, Shopping List and Settings. Replay it any time from Settings.",
        href: "/settings",
        cta: "Go to Settings",
      },
      {
        title: "A sample kitchen to explore",
        body: "New accounts start with 10 recipes, 4 meals, a planned Menu and the shopping list it makes. Remove or bring back the samples in Settings → Data Management.",
        href: "/settings?section=dataManagement",
        cta: "Manage samples",
      },
    ],
    improvements: [
      "“Meal Planner” is now called “Menu” throughout the app",
      "The Recipe Browser fits more recipes on screen, with sharper photos and easier navigation into each recipe",
      "Page headers look the same across the app and no longer overflow on small screens",
      "It's clearer which meal is selected on your Menu, and Shopping List items show their state more clearly",
      "Settings pages have been tidied up",
      "Home sections and unsent Genie messages are kept when you reload",
      "Your browser's back and forward buttons keep your place",
      "Backups now include your custom categories, ingredient units and unit conversions",
    ],
    fixes: [
      "The selected meal card is no longer cut off on desktop, and the meal panel scrolls when it's taller than your screen",
      "An interrupted recipe save picks up where it left off without creating a duplicate",
      "Settings save reliably, even when you change several quickly",
      "Signing in picks up an existing session instead of getting stuck",
      "Favorites stay saved",
      "Better error recovery and more accessible controls throughout the app",
    ],
  },
  {
    id: "2026-09-02",
    headline: "Small touches to Menu and billing",
    highlights: [
      {
        title: "Menu slots at a glance",
        body: "The Menu header shows how many of your 20 meal slots are in use.",
        href: "/meal-planner",
        cta: "Open Menu",
      },
    ],
    improvements: [
      "Plan & Billing shows your renewal date as soon as you subscribe — or, after cancelling, when your access ends",
    ],
    fixes: ["The meal carousel on Home is the right size on phones"],
  },
  {
    id: "2026-08-22",
    headline: "Filters that stick, and a round of fixes",
    highlights: [
      {
        title: "Recipe filters that stay put",
        body: "Your Recipe Browser search, filters and sort are still there when you leave and come back.",
        href: "/recipes",
        cta: "Browse recipes",
      },
    ],
    improvements: [
      "AI features retry automatically on temporary hiccups instead of hanging",
    ],
    fixes: [
      "Your Menu holds up to 20 planned meals, and finished meals waiting to be cleared don't count against the limit",
      "Recipe photos that were showing the wrong image have been fixed",
      "Items you add to the Shopping List join their category instead of landing in a duplicate “Other” section",
      "Genie tells you when it couldn't put together a full recipe, instead of handing you an empty one",
      "Swiping over a meal card on your phone scrolls the page instead of getting stuck",
    ],
  },
  {
    id: "2026-07-14",
    headline: "A new Home, and one place to build meals",
    highlights: [
      {
        title: "A new Home",
        body: "Home now centers on tonight's meal, with your cooking streak up top and a guided setup for new accounts.",
        href: "/dashboard",
        cta: "Go Home",
      },
      {
        title: "Build meals in one place",
        body: "One streamlined flow for creating meals — Recipe Roulette included for random picks — with a direct path from planning your week to your shopping list.",
        href: "/meal-planner?addMeal=1",
        cta: "Build a meal",
      },
      {
        title: "Import a recipe from a link",
        body: "Paste a link to an online recipe into the Recipe Wizard and it fills itself in.",
        href: "/recipes",
        cta: "Go to Recipes",
      },
    ],
    improvements: [
      "Choose a Light, Dark or System theme in Settings or the mobile menu — and no more dark flash when a page loads",
      "A floating Genie button keeps the assistant within reach on phones, plus a “Generate a recipe” shortcut in the Recipe Browser",
      "Better keyboard support on the Menu, reduced-motion support and clearer screen-reader labels",
      "A cleaner, easier-to-read font",
      "Settings only shows options that work, and About shows the real app version",
    ],
    fixes: [
      "AI badges tell AI-generated recipes apart from recipes that only have an AI-generated photo",
      "Printed recipes reliably include the recipe photo",
    ],
  },
  {
    id: "2026-06-23",
    headline: "The Recipe Wizard, and recipes written by Genie",
    highlights: [
      {
        title: "Recipe Wizard",
        body: "Create and edit recipes step by step: method, ingredients, directions and nutrition.",
        href: "/recipes",
        cta: "Go to Recipes",
      },
      {
        title: "Ask Genie for a recipe",
        body: "Genie writes a complete recipe draft, tailored to the recipes you already have, and drops it straight into the wizard.",
      },
      {
        title: "Nutrition facts",
        body: "Recipes show detailed nutrition information, and you can include it when you print.",
      },
    ],
    improvements: [
      "Create a meal from anywhere with the + button",
      "Total time is worked out for you from prep and cook times",
      "More accurate AI recipe photos",
      "Faster AI recipe generation, nutrition estimates and Genie replies",
      "Less lag when typing ingredients",
    ],
    fixes: ["Genie replies no longer fail after AI service updates"],
  },
  {
    id: "2026-03-24",
    headline: "A better phone experience",
    highlights: [
      {
        title: "A More menu on phones",
        body: "Tap More in the bottom bar for Settings, feedback, Genie and the rest of the app.",
      },
    ],
    improvements: [
      "Genie is easier to use on phones",
      "Genie stays out of the way on smaller screens until you need it",
    ],
  },
  {
    id: "2026-02-22",
    headline: "A new look, and categories of your own",
    highlights: [
      {
        title: "Top navigation",
        body: "Navigation moved to a bar across the top of the screen, with a + button for adding recipes and meals from anywhere.",
      },
      {
        title: "Your own categories and units",
        body: "Create recipe categories, ingredient categories and units that match how you cook and shop.",
        href: "/settings?section=recipePreferences",
        cta: "Open Settings",
      },
      {
        title: "Recipe groups",
        body: "Collect recipes into groups like “Weeknight Dinners” or “Holiday Favorites” and filter by them in the Recipe Browser.",
        href: "/recipes",
        cta: "Go to Recipes",
      },
    ],
    improvements: [
      "Long-press a meal on your Menu to drag it into a new spot",
      "Swipe through upcoming meals on Home",
      "Recipe filters stay visible as you scroll",
      "Recipes Genie created are marked with an AI badge",
      "Choose which recipe image to generate: the card photo or the banner",
      "Settings save instantly — no Save button needed",
      "Completing a meal automatically selects the next one on your Menu",
    ],
    fixes: [
      "Some ingredients no longer land in the wrong Shopping List category",
      "The feedback form submits reliably",
      "Autocomplete works for multi-word ingredients like “olive oil”",
      "Your cooking streak updates correctly when you clear completed meals",
      "Typing in the recipe form is more responsive",
    ],
  },
  {
    id: "2026-01-30",
    headline: "Meet Genie — plus backups and planning upgrades",
    highlights: [
      {
        title: "Meet Genie",
        body: "An AI assistant that knows your recipes, meals, Menu and shopping list. Ask for ideas, cooking tips or a brand-new recipe.",
      },
      {
        title: "Backup & restore",
        body: "Download a complete backup of your recipes, meals, Menu and shopping list from Settings → Data Management, and restore it any time.",
        href: "/settings?section=dataManagement",
        cta: "Open Data Management",
      },
      {
        title: "Recipe Roulette",
        body: "Can't decide? Let Roulette pick from your recipes, your Menu or your favorites.",
      },
    ],
    improvements: [
      "Tap the cart icon on a meal to include all its ingredients, only produce, or nothing in your Shopping List",
      "Flag Shopping List items as “don't forget” — they stay at the top of their category",
      "Genie's suggestions favor recipes you've already saved",
      "Quick Add on Home suggests ingredients as you type",
      "Every Shopping List category has its own icon, and recipe icons cover 25+ more foods",
      "Recipe pages open with a big banner photo",
      "See progress while a recipe photo is being generated",
      "Set your default recipe sort, servings and first day of the week in Settings",
      "Genie keeps your chat history between visits",
    ],
    fixes: [
      "Recipes print with the photo and text together on one page",
      "Flagged items stay flagged when your Menu changes",
      "Genie no longer creates duplicate recipes",
      "Meal suggestions on your Menu load every time",
      "Meal names are kept when you edit a meal",
    ],
  },
  {
    id: "2025-12-31",
    headline: "Where it all started",
    highlights: [
      {
        title: "A Shopping List that adds up",
        body: "Ingredients combine across recipes — cups with tablespoons, pounds with ounces — and quantities show as fractions.",
      },
      {
        title: "Cooking streak",
        body: "See how many days in a row you've cooked.",
      },
      {
        title: "Print recipes your way",
        body: "Choose whether to include the photo, notes and cook time.",
      },
    ],
    improvements: [
      "Add your own items to the Shopping List and pick their category",
      "Filter the Shopping List by recipe and see how much each recipe needs",
      "Hide collected items without losing them",
      "Favorite meals right from your Menu",
      "Custom unit conversions, like turning tablespoons of butter into sticks",
      "Choose which quick filters appear in the Recipe Browser",
      "Drag to reorder ingredients when editing a recipe",
    ],
  },
];

// ============================================
// Helpers
// ============================================

export const LATEST_RELEASE_ID = RELEASES[0]?.id ?? "";

/** "September 30, 2026" — the id's date part, read as a local calendar date */
export function formatReleaseDate(id: string): string {
  return new Date(`${id.slice(0, 10)}T00:00:00`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/** Releases newer than `lastSeenId` (all of them when nothing was seen). */
export function getUnreadReleaseIds(lastSeenId: string | null): Set<string> {
  return new Set(
    RELEASES.filter((release) => !lastSeenId || release.id > lastSeenId).map(
      (release) => release.id
    )
  );
}

/** "3 improvements · 2 fixes" — summary label for the collapsed lists */
export function describeMinorChanges(release: Release): string | null {
  const parts: string[] = [];
  const improvements = release.improvements?.length ?? 0;
  const fixes = release.fixes?.length ?? 0;
  if (improvements) parts.push(`${improvements} improvement${improvements === 1 ? "" : "s"}`);
  if (fixes) parts.push(`${fixes} fix${fixes === 1 ? "" : "es"}`);
  return parts.length ? parts.join(" · ") : null;
}
