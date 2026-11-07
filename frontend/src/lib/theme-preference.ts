import { LEGACY_THEME_STORAGE_KEY, THEME_STORAGE_KEY } from "@/lib/settings";

export type ThemePreference = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

/**
 * Explicit light/dark wins. Anything else — including "system", a missing
 * preference, or an unreadable value — follows the OS and falls back to light
 * when the OS does not say dark.
 */
export function resolveThemePreference(
  preference: string | null | undefined,
  prefersDark: boolean
): ResolvedTheme {
  if (preference === "light" || preference === "dark") return preference;
  return prefersDark ? "dark" : "light";
}

export function prefersDarkScheme(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/**
 * Blocking first-paint script. Keep the storage keys aligned with
 * settings-store.ts. An explicit saved light/dark/system value is honored;
 * no saved value follows the OS, with light as the fallback.
 */
export const themeInitScript = `(function () {
  try {
    var pref = null;
    var raw = localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});
    if (!raw) raw = localStorage.getItem("meal-genie-theme");
    if (raw) {
      try { pref = JSON.parse(raw); } catch (e) { pref = raw; }
    }
    if (pref !== "light" && pref !== "dark" && pref !== "system") {
      pref = localStorage.getItem(${JSON.stringify(LEGACY_THEME_STORAGE_KEY)});
    }
    var prefersDark = false;
    try {
      prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    } catch (e) {}
    var resolved = (pref === "light" || pref === "dark")
      ? pref
      : (prefersDark ? "dark" : "light");
    document.documentElement.classList.toggle("light", resolved === "light");
  } catch (e) {}
})();`;
