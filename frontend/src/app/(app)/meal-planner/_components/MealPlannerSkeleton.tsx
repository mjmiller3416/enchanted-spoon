import { Skeleton } from "@/components/ui/skeleton";

/**
 * MealGridSkeleton — placeholder matching the MealGrid card layout
 * (16/9 image + two text lines), shown while planner entries load.
 */
export function MealGridSkeleton() {
  return (
    <div className="@container">
      <div className="grid grid-cols-2 @2xl:grid-cols-3 @6xl:grid-cols-4 gap-4 auto-rows-fr">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="aspect-[16/9] w-full rounded-lg" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * MealPlannerSkeleton — full-page skeleton matching MealPlannerView's final
 * layout (PageLayout header + section heading + meal grid). Used by the route
 * loading boundary and the page-level Suspense fallback.
 */
export function MealPlannerSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <div className="pt-6 lg:pt-8 px-4 mx-auto max-w-7xl lg:max-w-none md:px-6">
        <div className="flex flex-col gap-1.5">
          <Skeleton className="h-8 w-44" />
          <Skeleton className="h-5 w-72" />
        </div>
      </div>
      <div className="max-w-7xl lg:max-w-none mx-auto px-4 md:px-6 py-6">
        <div className="space-y-4">
          <Skeleton className="h-6 w-40" />
          <MealGridSkeleton />
        </div>
      </div>
    </div>
  );
}
