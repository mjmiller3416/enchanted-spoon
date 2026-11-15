/** Routes where the mobile assistant button is shown. Exact matches only. */
export const ASSISTANT_FAB_ROUTES = ["/recipes", "/meal-planner"];

export function showsAssistantFab(pathname: string | null): boolean {
  return pathname != null && ASSISTANT_FAB_ROUTES.includes(pathname);
}

/**
 * Bottom padding for the app `<main>` on small screens.
 * Button routes reserve the floating control; every other page only
 * clears the bottom nav and its safe-area inset.
 */
export function mobileMainPaddingClass(pathname: string | null): string {
  return showsAssistantFab(pathname) ? "pb-mobile-fab" : "pb-mobile-nav";
}
