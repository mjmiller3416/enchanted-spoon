import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  CalendarDays,
  Compass,
  House,
  Plus,
  Search,
  Settings,
  ShoppingCart,
  SlidersHorizontal,
  Sparkles,
  UtensilsCrossed,
} from "lucide-react";

/**
 * One step of the onboarding tour.
 *
 * `targets` are `data-tour` tokens tried in order; the first one whose
 * element is actually visible wins. Elements can carry several
 * space-separated tokens (matched with `[data-tour~="token"]`), which is how
 * desktop-only targets fall back to their mobile equivalents: TopNav, the
 * md–xl hamburger, and MobileBottomNav all carry the same token and only one
 * is rendered visibly at any width. If nothing matches before the timeout,
 * the step shows as a centered card.
 */
export interface TourStepDefinition {
  id: string;
  /** Pathname the step lives on (query strings are ignored when matching) */
  route: string;
  targets: string[];
  title: string;
  description: string;
  icon: LucideIcon;
}

export const TOUR_STEPS: TourStepDefinition[] = [
  // ── Home ──────────────────────────────────────────────────────────────
  {
    id: "home-overview",
    route: "/dashboard",
    targets: ["home-get-started", "home-overview"],
    title: "Your kitchen at a glance",
    description:
      "Home shows tonight's meal, your shopping progress, and the week ahead. Until you've planned a meal, your Get Started checklist lives here.",
    icon: House,
  },
  {
    id: "navigation",
    route: "/dashboard",
    targets: ["nav-main"],
    title: "Get around",
    description:
      "Jump between Home, the Menu, Recipes, and your Shopping List from here.",
    icon: Compass,
  },

  // ── Recipes ───────────────────────────────────────────────────────────
  {
    id: "recipes-search",
    route: "/recipes",
    targets: ["recipes-search"],
    title: "Find any recipe",
    description:
      "Search by name, ingredient, or tag, and tap a quick filter like Favorites to narrow things down.",
    icon: Search,
  },
  {
    id: "recipes-filters",
    route: "/recipes",
    targets: ["recipes-filters"],
    title: "Sort and filter",
    description:
      "Sort your collection and open Filters for categories, meal types, dietary needs, and your recipe groups.",
    icon: SlidersHorizontal,
  },
  {
    id: "recipes-add",
    route: "/recipes",
    targets: ["recipes-add-empty", "nav-add"],
    title: "Add recipes your way",
    description:
      "Build one from scratch, paste a link to import it, or describe a dish and let AI draft it. The recipe wizard walks you through each step.",
    icon: Plus,
  },
  {
    id: "genie",
    route: "/recipes",
    targets: ["genie-trigger"],
    title: "Meet the Genie",
    description:
      "Your AI kitchen assistant. Ask the Genie for recipe ideas, cooking tips, or help planning the week.",
    icon: Sparkles,
  },

  // ── Meal planner + shopping ───────────────────────────────────────────
  {
    id: "planner-menu",
    route: "/meal-planner",
    targets: ["planner-menu"],
    title: "Plan your menu",
    description:
      "Meals you plan land here. Drag to reorder them, and mark each one cooked when it's done.",
    icon: CalendarDays,
  },
  {
    id: "planner-add-meal",
    route: "/meal-planner",
    targets: ["planner-add-meal"],
    title: "Build a meal",
    description:
      "Pair a main dish with up to three sides, then add it to your plan. You can save favorite combos to reuse.",
    icon: UtensilsCrossed,
  },
  {
    id: "shopping-list",
    route: "/shopping-list",
    targets: ["shopping-list"],
    title: "Your list builds itself",
    description:
      "Ingredients from planned meals are combined and grouped by store section. Add extras by hand and check items off as you shop.",
    icon: ShoppingCart,
  },

  // ── Settings ──────────────────────────────────────────────────────────
  {
    id: "settings-sections",
    route: "/settings",
    targets: ["settings-nav"],
    title: "Make it yours",
    description:
      "Switch themes in Appearance, tune the Genie in AI Features, back up your recipes in Data Management, and manage your plan in Plan & Billing.",
    icon: Settings,
  },
  {
    id: "settings-replay",
    route: "/settings",
    targets: ["settings-replay"],
    title: "That's the tour",
    description:
      "Replay it anytime from here or your account menu. Happy cooking!",
    icon: BookOpen,
  },
];
