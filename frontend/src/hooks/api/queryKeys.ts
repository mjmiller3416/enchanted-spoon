// src/hooks/api/queryKeys.ts
// Centralized query key factories for React Query cache management
//
// Query keys follow a hierarchical structure enabling targeted invalidation:
// - Invalidate plannerQueryKeys.all to clear ALL planner-related cache
// - Invalidate plannerQueryKeys.entries() to clear just the entries list
// - Invalidate plannerQueryKeys.meal(5) to clear just meal #5

export const plannerQueryKeys = {
  all: ["planner"] as const,
  entries: () => [...plannerQueryKeys.all, "entries"] as const,
  meal: (id: number) => [...plannerQueryKeys.all, "meal", id] as const,
  meals: () => [...plannerQueryKeys.all, "meals"] as const,
  savedMeals: () => [...plannerQueryKeys.all, "saved-meals"] as const,
  streak: () => [...plannerQueryKeys.all, "streak"] as const,
  summary: () => [...plannerQueryKeys.all, "summary"] as const,
};

export const recipeQueryKeys = {
  all: ["recipes"] as const,
  list: (filters?: Record<string, unknown>) =>
    filters
      ? ([...recipeQueryKeys.all, "list", filters] as const)
      : ([...recipeQueryKeys.all, "list"] as const),
  cards: (filters?: Record<string, unknown>) =>
    filters
      ? ([...recipeQueryKeys.all, "cards", filters] as const)
      : ([...recipeQueryKeys.all, "cards"] as const),
  detail: (id: number) => [...recipeQueryKeys.all, "detail", id] as const,
  categories: () => [...recipeQueryKeys.all, "categories"] as const,
  mealTypes: () => [...recipeQueryKeys.all, "meal-types"] as const,
};

export const dashboardQueryKeys = {
  all: ["dashboard"] as const,
  stats: () => [...dashboardQueryKeys.all, "stats"] as const,
};

export const categoryQueryKeys = {
  all: ["categories"] as const,
  lists: () => [...categoryQueryKeys.all, "list"] as const,
  list: (includeDisabled?: boolean) =>
    [...categoryQueryKeys.lists(), { includeDisabled }] as const,
  details: () => [...categoryQueryKeys.all, "detail"] as const,
  detail: (id: number) => [...categoryQueryKeys.details(), id] as const,
};

export const adminQueryKeys = {
  all: ["admin"] as const,
  users: () => [...adminQueryKeys.all, "users"] as const,
  usage: (month?: string) =>
    [...adminQueryKeys.all, "usage", month ?? "current"] as const,
};

export const currentUserQueryKeys = {
  all: ["currentUser"] as const,
  usage: () => [...currentUserQueryKeys.all, "usage"] as const,
};

// Re-export shopping keys for consistency
export { shoppingQueryKeys } from "./useShopping";
