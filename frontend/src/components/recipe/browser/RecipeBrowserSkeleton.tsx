import { Skeleton } from "@/components/ui/skeleton";

/**
 * RecipeBrowserSkeleton — full-page skeleton matching RecipeBrowserView's
 * final layout (hero, sort controls row, recipe card grid). Rendered by the
 * view's query-loading state, the route loading boundary, and the page-level
 * Suspense fallback so all three show identical UI (no double-flash).
 */
export function RecipeBrowserSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <Skeleton className="h-48 w-full" shape="none" />
      <div className="max-w-7xl mx-auto w-full px-4 md:px-6 py-6">
        <div className="mb-6">
          <Skeleton className="h-12 w-full" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 md:gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} size="card" className="h-64" />
          ))}
        </div>
        <span className="sr-only">Loading recipes...</span>
      </div>
    </div>
  );
}
