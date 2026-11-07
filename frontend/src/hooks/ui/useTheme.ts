"use client";

import { useCallback, useEffect, useState } from "react";
import {
  useSettings,
  LEGACY_THEME_STORAGE_KEY,
} from "@/hooks/persistence/useSettings";
import {
  prefersDarkScheme,
  resolveThemePreference,
  type ResolvedTheme,
  type ThemePreference,
} from "@/lib/theme-preference";

export type { ResolvedTheme, ThemePreference };

function resolveTheme(preference: ThemePreference): ResolvedTheme {
  return resolveThemePreference(preference, prefersDarkScheme());
}

function applyTheme(resolved: ResolvedTheme) {
  const root = document.documentElement;
  // Force all CSS variable changes into a single frame (see .no-transition in globals.css)
  root.classList.add("no-transition");
  root.classList.toggle("light", resolved === "light");
  requestAnimationFrame(() => {
    root.classList.remove("no-transition");
  });
}

interface UseThemeReturn {
  /** The user's stored preference, including "system" */
  theme: ThemePreference;
  /** The preference resolved against the OS setting — what's actually on screen */
  resolvedTheme: ResolvedTheme;
  /** Set an explicit preference (persists via the settings store) */
  setTheme: (preference: ThemePreference) => void;
  /** Binary flip of the currently resolved theme */
  toggleTheme: () => void;
}

/**
 * Single source of truth for theming.
 *
 * The preference lives in the settings store (`settings.appearance.theme`), so
 * the Settings page, the TopNav toggle, and the mobile More sheet can never
 * disagree — every instance syncs through useSettings' "settings-updated"
 * event and persists to localStorage + API through the same path.
 *
 * First paint is handled by the blocking inline script in the root layout;
 * this hook only keeps the DOM class in sync afterwards.
 */
export function useTheme(): UseThemeReturn {
  const { settings, updateSettings, isLoaded } = useSettings();
  const preference = settings.appearance.theme;

  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("light");

  // The blocking script owns the class until settings have loaded, so a saved
  // light or dark choice is not overwritten by the system default. After that,
  // this hook keeps the class in sync and follows OS changes while on system.
  useEffect(() => {
    if (!isLoaded) {
      setResolvedTheme(
        document.documentElement.classList.contains("light") ? "light" : "dark"
      );
      return;
    }

    const apply = () => {
      const resolved = resolveTheme(preference);
      setResolvedTheme(resolved);
      applyTheme(resolved);
    };
    apply();

    if (preference === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      mediaQuery.addEventListener("change", apply);
      return () => mediaQuery.removeEventListener("change", apply);
    }
  }, [preference, isLoaded]);

  // One-time migration off the pre-unification "theme" localStorage key
  useEffect(() => {
    if (!isLoaded) return;
    const legacy = localStorage.getItem(LEGACY_THEME_STORAGE_KEY);
    if (legacy !== "light" && legacy !== "dark") return;
    localStorage.removeItem(LEGACY_THEME_STORAGE_KEY);
    if (legacy !== preference) {
      updateSettings("appearance", { theme: legacy });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- migration runs once, when settings finish loading
  }, [isLoaded]);

  const setTheme = useCallback(
    (next: ThemePreference) => {
      updateSettings("appearance", { theme: next });
    },
    [updateSettings]
  );

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === "light" ? "dark" : "light");
  }, [resolvedTheme, setTheme]);

  return { theme: preference, resolvedTheme, setTheme, toggleTheme };
}
