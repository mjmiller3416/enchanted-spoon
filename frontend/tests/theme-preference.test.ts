import { afterEach, describe, expect, it } from "vitest";
import { resolveThemePreference, themeInitScript } from "@/lib/theme-preference";

function setPrefersDark(prefersDark: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: query === "(prefers-color-scheme: dark)" ? prefersDark : false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
      onchange: null,
    }),
  });
}

function runInitScript() {
  document.documentElement.classList.remove("light");
  window.eval(themeInitScript);
}

afterEach(() => {
  localStorage.clear();
  document.documentElement.classList.remove("light");
});

describe("resolveThemePreference", () => {
  it("keeps an explicit light or dark choice", () => {
    expect(resolveThemePreference("light", true)).toBe("light");
    expect(resolveThemePreference("dark", false)).toBe("dark");
  });

  it("follows the OS for system and for a first visit, and falls back to light", () => {
    expect(resolveThemePreference("system", true)).toBe("dark");
    expect(resolveThemePreference("system", false)).toBe("light");
    expect(resolveThemePreference(null, false)).toBe("light");
    expect(resolveThemePreference(undefined, true)).toBe("dark");
    expect(resolveThemePreference("nope", false)).toBe("light");
  });
});

describe("themeInitScript", () => {
  it("uses light when nothing is saved and the OS is not dark", () => {
    setPrefersDark(false);
    runInitScript();
    expect(document.documentElement.classList.contains("light")).toBe(true);
  });

  it("uses dark when nothing is saved and the OS prefers dark", () => {
    setPrefersDark(true);
    runInitScript();
    expect(document.documentElement.classList.contains("light")).toBe(false);
  });

  it("honors a saved explicit theme over the OS", () => {
    setPrefersDark(true);
    localStorage.setItem("enchanted-spoon-theme", JSON.stringify("light"));
    runInitScript();
    expect(document.documentElement.classList.contains("light")).toBe(true);

    localStorage.setItem("enchanted-spoon-theme", JSON.stringify("dark"));
    setPrefersDark(false);
    runInitScript();
    expect(document.documentElement.classList.contains("light")).toBe(false);
  });

  it("treats a saved system preference as the OS, with light as the fallback", () => {
    localStorage.setItem("enchanted-spoon-theme", JSON.stringify("system"));
    setPrefersDark(false);
    runInitScript();
    expect(document.documentElement.classList.contains("light")).toBe(true);

    setPrefersDark(true);
    runInitScript();
    expect(document.documentElement.classList.contains("light")).toBe(false);
  });
});
