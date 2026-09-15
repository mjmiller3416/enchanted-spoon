export interface UserProfile {
  userName: string;
  email: string;
  avatar: string; // URL or empty string
}

export interface AppearanceSettings {
  theme: "light" | "dark" | "system";
  // Future: accentColor, fontSize, etc.
}

export interface RecipePreferences {
  defaultSortOrder: "alphabetical" | "recent" | "cookTime";
  quickFilters: string[]; // IDs of quick filters to display (max 5)
}

export interface ShoppingListSettings {
  categorySortOrder: "alphabetical" | "custom";
  customCategoryOrder: string[]; // User-defined order for shopping list categories
  autoClearChecked: "manual" | "onRefresh" | "daily";
  hideCompleted: boolean;
}

export interface AIFeaturesSettings {
  imageGenerationPrompt: string;
  /** Floating "Ask the Genie" button on mobile Recipes/Planner pages */
  showAssistantFab: boolean;
}

export interface AppSettings {
  profile: UserProfile;
  appearance: AppearanceSettings;
  recipePreferences: RecipePreferences;
  shoppingList: ShoppingListSettings;
  aiFeatures: AIFeaturesSettings;
}

// ============================================================================
// DEFAULT VALUES
// ============================================================================

export const DEFAULT_SETTINGS: AppSettings = {
  profile: {
    userName: "User",
    email: "",
    avatar: "",
  },
  appearance: {
    theme: "dark",
  },
  recipePreferences: {
    defaultSortOrder: "alphabetical",
    quickFilters: ["breakfast", "lunch", "dinner", "sides", "new"],
  },
  shoppingList: {
    categorySortOrder: "alphabetical",
    customCategoryOrder: [
      "Produce",
      "Bakery",
      "Deli",
      "Dairy",
      "Meat",
      "Seafood",
      "Frozen",
      "Pantry",
      "Condiments",
      "Oils and Vinegars",
      "Spices",
      "Baking",
      "Beverages",
      "Other",
    ],
    autoClearChecked: "manual",
    hideCompleted: false,
  },
  aiFeatures: {
    imageGenerationPrompt:
      "A professional cookbook-quality food photograph of {recipe_name}. Style the scene — surface, props, lighting, and camera angle — to match the character of this specific dish. Vary the composition naturally: choose whichever angle, surface, and props a professional food stylist would select for this recipe. Shallow depth of field, natural light, appetizing presentation, high detail, no people, no hands, no text, square format.",
    showAssistantFab: true,
  },
};

// ============================================================================
// STORAGE KEYS
// ============================================================================

export const SETTINGS_STORAGE_KEY = "enchanted-spoon-settings";
export const THEME_STORAGE_KEY = "enchanted-spoon-theme"; // Separate key for instant theme load (read by the blocking script in the root layout — keep that script in sync)
export const LEGACY_THEME_STORAGE_KEY = "theme"; // Pre-unification key written by the old TopNav toggle
// Pre-rename (Meal Genie era) keys, migrated on first load — drop the shims after 1-2 releases


export function deepMergeSettings(defaults: AppSettings, source: SettingsPatch): AppSettings {
  return {
    profile: {
      ...defaults.profile,
      ...(source.profile || {}),
    },
    appearance: {
      ...defaults.appearance,
      ...(source.appearance || {}),
    },
    recipePreferences: {
      ...defaults.recipePreferences,
      ...(source.recipePreferences || {}),
    },
    shoppingList: {
      ...defaults.shoppingList,
      ...(source.shoppingList || {}),
    },
    aiFeatures: {
      ...defaults.aiFeatures,
      ...(source.aiFeatures || {}),
    },
  };
}

export type SettingsPatch = { [K in keyof AppSettings]?: Partial<AppSettings[K]> };
