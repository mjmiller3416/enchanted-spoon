/**
 * Mobile meal-detail sheet (Menu, below the lg breakpoint).
 *
 * The sheet fills the dynamic viewport and scrolls. With viewport-fit=cover
 * its bottom edge lies under the system home indicator / navigation bar, and
 * the scroll ends with the last actions in that inset, so they cannot be
 * brought fully on screen. The body keeps today's 1rem padding and adds the
 * inset, which is 0 when the system reports none.
 *
 * The in-app bottom nav paints underneath this sheet, so the padding does not
 * also reserve the nav. From md up that nav is hidden anyway; subtracting it
 * would open a gap on tablet sheets. The desktop detail pane does not use
 * these classes.
 */
export const MEAL_DETAIL_SHEET_BODY_REM = 1;

export const MEAL_DETAIL_SHEET_CLASS = "h-dvh max-h-dvh overflow-y-auto";

export const MEAL_DETAIL_SHEET_BODY_CLASS =
  "px-4 pt-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))]";

const REM_PX = 16;

/**
 * Bottom edge of the meal card once the sheet is scrolled to the end.
 * The sheet is bottom-anchored at 100dvh, and the card sits above the body
 * padding (1rem + the system inset).
 */
export function mealDetailCardBottom(viewportHeight: number, safeAreaBottom: number): number {
  return viewportHeight - (MEAL_DETAIL_SHEET_BODY_REM * REM_PX + safeAreaBottom);
}
