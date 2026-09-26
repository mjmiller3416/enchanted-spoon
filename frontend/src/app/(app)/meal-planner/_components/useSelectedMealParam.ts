"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** Search param holding the open meal's planner entry id */
export const MEAL_PARAM = "meal";

interface SelectedMealParam {
  /** Planner entry id from `?meal=`, or null when no meal is open */
  selectedEntryId: number | null;
  /** Open (or swap to) a planner entry, preserving any other search params */
  openMeal: (entryId: number) => void;
  /** Close the open meal by removing `?meal=`, preserving any other search params */
  closeMeal: () => void;
}

/**
 * useSelectedMealParam - URL-driven selection for the Menu page.
 *
 * The open meal lives in `?meal=<plannerEntryId>` so it survives refresh and
 * can be linked to. Updates use `router.replace` (no history entries, no
 * scroll jump); no param means the detail pane / sheet is closed. Malformed
 * values read as null; ids that no longer exist are closed by the caller.
 */
export function useSelectedMealParam(): SelectedMealParam {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const raw = searchParams.get(MEAL_PARAM);
  const parsed = raw !== null ? Number(raw) : NaN;
  const selectedEntryId = Number.isInteger(parsed) && parsed > 0 ? parsed : null;

  // Write the param, reading the live URL so back-to-back updates in the same
  // tick (e.g. addMeal cleanup + selection) don't clobber each other
  const replaceParam = useCallback(
    (entryId: number | null) => {
      const params = new URLSearchParams(window.location.search);
      if (entryId === null) params.delete(MEAL_PARAM);
      else params.set(MEAL_PARAM, String(entryId));
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [router, pathname]
  );

  const openMeal = useCallback((entryId: number) => replaceParam(entryId), [replaceParam]);
  const closeMeal = useCallback(() => replaceParam(null), [replaceParam]);

  return { selectedEntryId, openMeal, closeMeal };
}
