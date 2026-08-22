"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { useDebouncedCallback } from "use-debounce";
import { settingsApi } from "@/lib/api";
import { migrateLocalStorageKey } from "./useLocalStorageState";

// Auto-save debounce delay (ms)
const AUTO_SAVE_DELAY = 500;

// ============================================================================
// TYPES
// ============================================================================

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
export const THEME_STORAGE_KEY = "meal-genie-theme"; // Separate key for instant theme load (read by the blocking script in the root layout)
export const LEGACY_THEME_STORAGE_KEY = "theme"; // Pre-unification key written by the old TopNav toggle
// Pre-rename (Meal Genie era) key, migrated on first load — drop the shim after 1-2 releases
const LEGACY_SETTINGS_STORAGE_KEY = "meal-genie-settings";

// ============================================================================
// HOOK
// ============================================================================

interface UseSettingsReturn {
  /**
   * Current settings state
   */
  settings: AppSettings;
  /**
   * Whether settings have been loaded from storage/API
   */
  isLoaded: boolean;
  /**
   * Whether settings are currently being fetched from the API
   * (UI can show skeleton during initial load)
   */
  isLoading: boolean;
  /**
   * Whether settings are currently being synced to the API
   */
  isSyncing: boolean;
  /**
   * Update a specific section of settings (auto-saves after debounce)
   */
  updateSettings: <K extends keyof AppSettings>(
    section: K,
    values: Partial<AppSettings[K]>
  ) => void;
  /**
   * Update multiple sections at once (auto-saves after debounce)
   */
  updateMultipleSections: (updates: Partial<AppSettings>) => void;
  /**
   * Reset settings to defaults (auto-saves immediately)
   */
  resetSettings: () => void;
  /**
   * Reset a specific section to defaults (auto-saves immediately)
   */
  resetSection: <K extends keyof AppSettings>(section: K) => void;
}

/**
 * Hook for managing application settings with auto-save, API sync, and localStorage fallback.
 *
 * Behavior:
 * - **Auto-save**: Changes are automatically persisted after a 500ms debounce
 * - Theme is ALWAYS stored in localStorage for instant load (prevents flash)
 * - When signed in: fetches settings from API, syncs changes to API
 * - When signed out: falls back to localStorage
 * - Graceful degradation: if API fails, falls back to localStorage
 *
 * @example
 * ```tsx
 * const { settings, updateSettings, isLoading, isSyncing } = useSettings();
 *
 * // Update profile - automatically saves after debounce
 * updateSettings('profile', { userName: 'John' });
 *
 * // Reset a section - saves immediately
 * resetSection('appearance');
 * ```
 */
export function useSettings(): UseSettingsReturn {
  const { isSignedIn, isLoaded: isAuthLoaded, getToken } = useAuth();

  const [settings, setSettings] = useState<AppSettings>(() => {
    // Initialize with theme from localStorage for instant apply (SSR-safe)
    if (typeof window !== "undefined") {
      // Runs before any read in this hook, so loadFromLocalStorage always
      // sees the new key (initializers execute ahead of the load effect)
      migrateLocalStorageKey(LEGACY_SETTINGS_STORAGE_KEY, SETTINGS_STORAGE_KEY);
      try {
        const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
        if (storedTheme) {
          const theme = JSON.parse(storedTheme) as AppearanceSettings["theme"];
          return {
            ...DEFAULT_SETTINGS,
            appearance: { ...DEFAULT_SETTINGS.appearance, theme },
          };
        }
        const legacyTheme = localStorage.getItem(LEGACY_THEME_STORAGE_KEY);
        if (legacyTheme === "light" || legacyTheme === "dark") {
          return {
            ...DEFAULT_SETTINGS,
            appearance: { ...DEFAULT_SETTINGS.appearance, theme: legacyTheme },
          };
        }
      } catch {
        // Ignore parse errors
      }
    }
    return DEFAULT_SETTINGS;
  });
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  // Track if we've already loaded settings this session
  const hasLoadedRef = useRef(false);

  // Ref to hold current settings for the debounced save (avoids stale closure)
  const settingsRef = useRef<AppSettings>(settings);
  settingsRef.current = settings;

  // Load settings on mount - from API if signed in, otherwise localStorage
  useEffect(() => {
    // Wait for auth to load before fetching
    if (!isAuthLoaded) return;
    // Only load once per session
    if (hasLoadedRef.current) return;

    async function loadSettings() {
      setIsLoading(true);
      hasLoadedRef.current = true;

      try {
        if (isSignedIn) {
          // Try to fetch from API
          const token = await getToken();
          const apiSettings = await settingsApi.get(token);

          if (apiSettings && Object.keys(apiSettings).length > 0) {
            // API returned settings - merge with defaults
            const merged = deepMergeSettings(DEFAULT_SETTINGS, apiSettings as Partial<AppSettings>);
            setSettings(merged);

            // Also save theme to localStorage for instant load on refresh
            localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(merged.appearance.theme));
            // Keep full settings in localStorage as fallback
            localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(merged));
          } else {
            // API returned empty - load from localStorage and sync to API
            const localSettings = loadFromLocalStorage();
            setSettings(localSettings);

            // Sync localStorage settings to API for first-time users
            try {
              await settingsApi.replace(localSettings as unknown as Record<string, unknown>, token);
            } catch {
              console.warn("[useSettings] Failed to sync initial settings to API");
            }
          }
        } else {
          // Not signed in - use localStorage
          const localSettings = loadFromLocalStorage();
          setSettings(localSettings);
        }
      } catch (error) {
        console.error("[useSettings] Failed to load settings from API:", error);
        // Fallback to localStorage
        const localSettings = loadFromLocalStorage();
        setSettings(localSettings);
      } finally {
        setIsLoading(false);
        setIsLoaded(true);
      }
    }

    loadSettings();
  }, [isAuthLoaded, isSignedIn, getToken]);

  // Keep every useSettings instance in sync: when any instance persists (or a
  // backup restore dispatches "settings-updated"), adopt the new snapshot so a
  // stale instance never clobbers another instance's changes on its next save.
  useEffect(() => {
    const handleSettingsUpdated = (event: Event) => {
      const detail = (event as CustomEvent<AppSettings>).detail;
      if (!detail) return;
      setSettings(deepMergeSettings(DEFAULT_SETTINGS, detail));
    };
    window.addEventListener("settings-updated", handleSettingsUpdated);
    return () => window.removeEventListener("settings-updated", handleSettingsUpdated);
  }, []);

  // Persist settings to localStorage and API
  const persistSettings = useCallback(
    async (settingsToSave: AppSettings) => {
      // Always save theme to localStorage for instant load
      localStorage.setItem(THEME_STORAGE_KEY, JSON.stringify(settingsToSave.appearance.theme));
      // Always save full settings to localStorage as fallback
      localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settingsToSave));

      // Dispatch event for other components to react
      window.dispatchEvent(new CustomEvent("settings-updated", { detail: settingsToSave }));

      // If signed in, sync to API
      if (isSignedIn) {
        setIsSyncing(true);
        try {
          const token = await getToken();
          await settingsApi.replace(settingsToSave as unknown as Record<string, unknown>, token);
        } catch (error) {
          console.error("[useSettings] Failed to sync settings to API:", error);
          // Settings are already saved locally, so this is a silent failure
        } finally {
          setIsSyncing(false);
        }
      }
    },
    [isSignedIn, getToken]
  );

  // Debounced auto-save (triggers after user stops making changes)
  const debouncedPersist = useDebouncedCallback(() => {
    persistSettings(settingsRef.current);
  }, AUTO_SAVE_DELAY);

  // Update a specific section (auto-saves after debounce)
  const updateSettings = useCallback(
    <K extends keyof AppSettings>(section: K, values: Partial<AppSettings[K]>) => {
      setSettings((prev) => ({
        ...prev,
        [section]: {
          ...prev[section],
          ...values,
        },
      }));
      debouncedPersist();
    },
    [debouncedPersist]
  );

  // Update multiple sections at once (auto-saves after debounce)
  const updateMultipleSections = useCallback(
    (updates: Partial<AppSettings>) => {
      setSettings((prev) => {
        const newSettings = { ...prev };

        if (updates.profile) {
          newSettings.profile = { ...prev.profile, ...updates.profile };
        }
        if (updates.appearance) {
          newSettings.appearance = { ...prev.appearance, ...updates.appearance };
        }
        if (updates.recipePreferences) {
          newSettings.recipePreferences = { ...prev.recipePreferences, ...updates.recipePreferences };
        }
        if (updates.shoppingList) {
          newSettings.shoppingList = { ...prev.shoppingList, ...updates.shoppingList };
        }
        if (updates.aiFeatures) {
          newSettings.aiFeatures = { ...prev.aiFeatures, ...updates.aiFeatures };
        }

        return newSettings;
      });
      debouncedPersist();
    },
    [debouncedPersist]
  );

  // Reset all settings to defaults (saves immediately)
  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
    // Save immediately (no debounce for reset)
    persistSettings(DEFAULT_SETTINGS);
  }, [persistSettings]);

  // Reset a specific section to defaults (saves immediately)
  const resetSection = useCallback(
    <K extends keyof AppSettings>(section: K) => {
      setSettings((prev) => {
        const newSettings = {
          ...prev,
          [section]: DEFAULT_SETTINGS[section],
        };
        // Save immediately (no debounce for reset)
        persistSettings(newSettings);
        return newSettings;
      });
    },
    [persistSettings]
  );

  return {
    settings,
    isLoaded,
    isLoading,
    isSyncing,
    updateSettings,
    updateMultipleSections,
    resetSettings,
    resetSection,
  };
}

/**
 * Load settings from localStorage with defaults merge
 */
function loadFromLocalStorage(): AppSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as Partial<AppSettings>;
      return deepMergeSettings(DEFAULT_SETTINGS, parsed);
    }
  } catch (error) {
    console.error("[useSettings] Failed to load from localStorage:", error);
  }
  return DEFAULT_SETTINGS;
}

// ============================================================================
// HELPERS
// ============================================================================

/**
 * Deep merge settings with defaults, ensuring all required fields exist
 */
function deepMergeSettings(defaults: AppSettings, source: Partial<AppSettings>): AppSettings {
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