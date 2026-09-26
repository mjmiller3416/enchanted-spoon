import type { Metadata } from "next";
import { Suspense } from "react";
import { MealPlannerView } from "@/app/(app)/meal-planner/_components";
import { MealPlannerSkeleton } from "./_components/MealPlannerSkeleton";

export const metadata: Metadata = { title: "Menu" };

/**
 * Meal Planner Page
 *
 * Route: /meal-planner
 *
 * Suspense is required because MealPlannerView reads search params
 * (?addMeal=1 auto-opens the meal creation flow).
 */
export default function Page() {
  return (
    <Suspense fallback={<MealPlannerSkeleton />}>
      <MealPlannerView />
    </Suspense>
  );
}
