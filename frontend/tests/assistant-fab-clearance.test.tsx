import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { AssistantFab } from "@/components/assistant/AssistantFab";
import {
  mobileMainPaddingClass,
  showsAssistantFab,
} from "@/components/layout/mobileChrome";

let pathname = "/meal-planner";
let showAssistantFab = true;

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

vi.mock("@/hooks/persistence", () => ({
  useSettings: () => ({
    isLoaded: true,
    settings: { aiFeatures: { showAssistantFab } },
  }),
}));

vi.mock("@/lib/providers/AssistantProvider", () => ({
  useAssistantDialog: () => ({ openAssistant: vi.fn() }),
}));

const NAV_REM = 4;
const GAP_ABOVE_NAV_REM = 2;
const FAB_REM = 3;
const GAP_ABOVE_FAB_REM = 1;
const REM_PX = 16;

const css = readFileSync(join(process.cwd(), "src/app/globals.css"), "utf8");

function chrome(safeAreaBottom: number) {
  const nav = NAV_REM * REM_PX + safeAreaBottom;
  const fabBottom = (NAV_REM + GAP_ABOVE_NAV_REM) * REM_PX + safeAreaBottom;
  const fabTop = fabBottom + FAB_REM * REM_PX;
  const contentEnd = (NAV_REM + GAP_ABOVE_NAV_REM + FAB_REM + GAP_ABOVE_FAB_REM) * REM_PX + safeAreaBottom;
  return { nav, fabBottom, fabTop, contentEnd };
}

afterEach(() => {
  cleanup();
  pathname = "/meal-planner";
  showAssistantFab = true;
});

describe("assistant button clearance", () => {
  it("keeps the button above the nav inset and the last cards above the button", () => {
    expect(css).toContain(
      "bottom: calc(4rem + 2rem + env(safe-area-inset-bottom, 0px))",
    );
    expect(css).toContain(
      "padding-bottom: calc(5rem + env(safe-area-inset-bottom, 0px))",
    );
    expect(css).toContain(
      "padding-bottom: calc(4rem + 2rem + 3rem + 1rem + env(safe-area-inset-bottom, 0px))",
    );

    const phones = [
      { name: "audit android", width: 402, height: 874, safeAreaBottom: 0 },
      { name: "audit android gesture", width: 402, height: 874, safeAreaBottom: 48 },
      { name: "small android", width: 360, height: 800, safeAreaBottom: 0 },
      { name: "small android 3-button", width: 360, height: 640, safeAreaBottom: 48 },
      { name: "pixel 7", width: 412, height: 915, safeAreaBottom: 24 },
      { name: "iphone se", width: 375, height: 667, safeAreaBottom: 0 },
      { name: "iphone 14", width: 390, height: 844, safeAreaBottom: 34 },
      { name: "iphone 14 pro", width: 393, height: 852, safeAreaBottom: 34 },
      { name: "iphone 16", width: 402, height: 874, safeAreaBottom: 34 },
    ];

    for (const phone of phones) {
      const { nav, fabBottom, fabTop, contentEnd } = chrome(phone.safeAreaBottom);
      expect(fabBottom - nav, phone.name).toBe(GAP_ABOVE_NAV_REM * REM_PX);
      expect(contentEnd - fabTop, phone.name).toBe(GAP_ABOVE_FAB_REM * REM_PX);
      expect(fabTop, phone.name).toBeLessThan(phone.height);
      expect(nav + FAB_REM * REM_PX, phone.name).toBeLessThan(phone.height);
    }
  });

  it("reserves button clearance only on the recipes and menu screens", () => {
    expect(showsAssistantFab("/recipes")).toBe(true);
    expect(showsAssistantFab("/meal-planner")).toBe(true);
    expect(showsAssistantFab("/recipes/42")).toBe(false);
    expect(showsAssistantFab("/dashboard")).toBe(false);
    expect(mobileMainPaddingClass("/recipes")).toBe("pb-mobile-fab");
    expect(mobileMainPaddingClass("/meal-planner")).toBe("pb-mobile-fab");
    expect(mobileMainPaddingClass("/recipes/42")).toBe("pb-mobile-nav");
    expect(mobileMainPaddingClass("/shopping-list")).toBe("pb-mobile-nav");
  });

  it("renders the button above the nav on menu and recipes, and nowhere else", () => {
    pathname = "/meal-planner";
    const { unmount } = render(<AssistantFab />);
    const button = screen.getByRole("button", { name: "Ask the Genie" });
    expect(button.className).toContain("bottom-above-mobile-nav");
    expect(button.className).toContain("size-12");
    expect(button.className).not.toContain("bottom-24");
    unmount();

    pathname = "/recipes";
    render(<AssistantFab />);
    expect(screen.getByRole("button", { name: "Ask the Genie" })).toBeTruthy();
    cleanup();

    pathname = "/recipes/42";
    render(<AssistantFab />);
    expect(screen.queryByRole("button", { name: "Ask the Genie" })).toBeNull();
    cleanup();

    pathname = "/dashboard";
    render(<AssistantFab />);
    expect(screen.queryByRole("button", { name: "Ask the Genie" })).toBeNull();
    cleanup();

    pathname = "/meal-planner";
    showAssistantFab = false;
    render(<AssistantFab />);
    expect(screen.queryByRole("button", { name: "Ask the Genie" })).toBeNull();
  });
});
