import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  MEAL_DETAIL_SHEET_BODY_CLASS,
  MEAL_DETAIL_SHEET_BODY_REM,
  MEAL_DETAIL_SHEET_CLASS,
  mealDetailCardBottom,
} from "@/app/(app)/meal-planner/_components/mealDetailSheet";

const REM_PX = 16;

const view = readFileSync(
  join(process.cwd(), "src/app/(app)/meal-planner/_components/MealPlannerView.tsx"),
  "utf8",
);

const phones = [
  { name: "audit iphone", width: 402, height: 874 },
  { name: "small android", width: 360, height: 800 },
  { name: "small android short", width: 360, height: 640 },
  { name: "iphone se", width: 375, height: 667 },
  { name: "iphone 14", width: 390, height: 844 },
  { name: "pixel", width: 412, height: 915 },
];

const insets = [0, 24, 34, 48];

describe("meal detail sheet clearance", () => {
  it("scrolls a dynamic viewport and pads the last row by the safe-area inset", () => {
    expect(MEAL_DETAIL_SHEET_CLASS).toContain("h-dvh");
    expect(MEAL_DETAIL_SHEET_CLASS).toContain("max-h-dvh");
    expect(MEAL_DETAIL_SHEET_CLASS).toContain("overflow-y-auto");
    expect(MEAL_DETAIL_SHEET_CLASS).not.toContain("overflow-hidden");
    expect(MEAL_DETAIL_SHEET_CLASS).not.toMatch(/h-screen|100vh/);
    expect(MEAL_DETAIL_SHEET_BODY_CLASS).toBe(
      `px-4 pt-4 pb-[calc(${MEAL_DETAIL_SHEET_BODY_REM}rem+env(safe-area-inset-bottom,0px))]`,
    );
    // The in-app nav is under the sheet and hidden from md up. Reserving it
    // would leave a gap on tablet sheets.
    expect(MEAL_DETAIL_SHEET_CLASS).not.toContain("4rem");
    expect(MEAL_DETAIL_SHEET_BODY_CLASS).not.toContain("4rem");

    expect(view).toContain(`className={MEAL_DETAIL_SHEET_CLASS}`);
    expect(view).toContain(`className={MEAL_DETAIL_SHEET_BODY_CLASS}`);
    expect(view).toContain("!isDesktop && (");
    expect(view).toContain('useMediaQuery("(min-width: 1024px)")');
  });

  it("keeps the meal card above the system inset on small portrait phones", () => {
    for (const phone of phones) {
      expect(phone.width, phone.name).toBeLessThan(1024);
      for (const inset of insets) {
        const cardBottom = mealDetailCardBottom(phone.height, inset);
        const safeLine = phone.height - inset;
        expect(cardBottom, `${phone.name} inset ${inset}`).toBe(
          phone.height - (MEAL_DETAIL_SHEET_BODY_REM * REM_PX + inset),
        );
        expect(cardBottom, `${phone.name} inset ${inset}`).toBeLessThanOrEqual(safeLine);
        expect(safeLine - cardBottom, `${phone.name} inset ${inset}`).toBe(
          MEAL_DETAIL_SHEET_BODY_REM * REM_PX,
        );
      }
    }
  });

  it("does not add space when the system inset is zero", () => {
    for (const height of [640, 667, 800, 844, 874, 915, 1024]) {
      expect(mealDetailCardBottom(height, 0)).toBe(height - MEAL_DETAIL_SHEET_BODY_REM * REM_PX);
    }
  });
});
