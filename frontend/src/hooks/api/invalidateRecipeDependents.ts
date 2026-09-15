import type { QueryClient } from "@tanstack/react-query";
import { recipeQueryKeys, plannerQueryKeys, shoppingQueryKeys, dashboardQueryKeys } from "./queryKeys";

/** Recipe content is embedded in meals, planner entries, and shopping sources. */
export function invalidateRecipeDependents(client: QueryClient) {
  return Promise.all([recipeQueryKeys.all, plannerQueryKeys.all, shoppingQueryKeys.all, dashboardQueryKeys.all]
    .map(queryKey => client.invalidateQueries({ queryKey })));
}
