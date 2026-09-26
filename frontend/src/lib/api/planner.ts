import type {
  MealSelectionResponseDTO,
  MealSelectionCreateDTO,
  MealSelectionUpdateDTO,
  MealPlanSummaryDTO,
} from "@/types/meal";
import type { PlannerEntryResponseDTO } from "@/types/planner";
import type { CookingStreakDTO } from "@/types/recipe";
import { fetchApi } from "./base";

export const plannerApi = {
  /**
   * Get all meals, optionally filtered by saved status
   * @param filters - Optional filter parameters
   * @param token - Optional auth token for authenticated requests
   */
  getMeals: (filters?: { saved?: boolean }, token?: string | null): Promise<MealSelectionResponseDTO[]> => {
    const query = filters?.saved !== undefined ? `?saved=${filters.saved}` : "";
    return fetchApi<MealSelectionResponseDTO[]>(`/api/meals${query}`, undefined, token);
  },

  /**
   * Get planner summary
   * @param token - Optional auth token for authenticated requests
   */
  getSummary: (token?: string | null): Promise<MealPlanSummaryDTO> =>
    fetchApi<MealPlanSummaryDTO>("/api/planner/summary", undefined, token),

  /**
   * Get a single meal
   * @param id - Meal ID
   * @param token - Optional auth token for authenticated requests
   */
  getMeal: (id: number, token?: string | null): Promise<MealSelectionResponseDTO> =>
    fetchApi<MealSelectionResponseDTO>(`/api/meals/${id}`, undefined, token),

  /**
   * Create a new meal
   * @param data - Meal data
   * @param token - Optional auth token for authenticated requests
   */
  createMeal: (data: MealSelectionCreateDTO, token?: string | null): Promise<MealSelectionResponseDTO> =>
    fetchApi<MealSelectionResponseDTO>(
      "/api/meals",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token
    ),

  /**
   * Update an existing meal
   * @param id - Meal ID
   * @param data - Meal data to update
   * @param token - Optional auth token for authenticated requests
   */
  updateMeal: (
    id: number,
    data: MealSelectionUpdateDTO,
    token?: string | null
  ): Promise<MealSelectionResponseDTO> =>
    fetchApi<MealSelectionResponseDTO>(
      `/api/meals/${id}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
      token
    ),

  /**
   * Delete a meal
   * @param id - Meal ID
   * @param token - Optional auth token for authenticated requests
   */
  deleteMeal: (id: number, token?: string | null): Promise<void> =>
    fetchApi<void>(`/api/meals/${id}`, { method: "DELETE" }, token),

  /**
   * Toggle meal saved status (saved meals persist after leaving planner)
   * @param id - Meal ID
   * @param token - Optional auth token for authenticated requests
   */
  toggleSave: (id: number, token?: string | null): Promise<MealSelectionResponseDTO> =>
    fetchApi<MealSelectionResponseDTO>(
      `/api/meals/${id}/save`,
      {
        method: "POST",
      },
      token
    ),

  /**
   * Add a recipe as a side dish to a meal
   * @param mealId - Meal ID
   * @param recipeId - Recipe ID to add as side
   * @param token - Optional auth token for authenticated requests
   */
  addSideToMeal: (mealId: number, recipeId: number, token?: string | null): Promise<MealSelectionResponseDTO> =>
    fetchApi<MealSelectionResponseDTO>(
      `/api/meals/${mealId}/sides/${recipeId}`,
      {
        method: "POST",
      },
      token
    ),

  /**
   * Clear planner entries
   * @param token - Optional auth token for authenticated requests
   */
  clearPlan: (token?: string | null): Promise<void> =>
    fetchApi<void>("/api/planner/clear", { method: "DELETE" }, token),

  /**
   * Remove a meal from the planner by meal ID (meal persists in Meals table)
   * @param mealId - Meal ID
   * @param token - Optional auth token for authenticated requests
   */
  removeFromPlanner: (mealId: number, token?: string | null): Promise<{ message: string }> =>
    fetchApi<{ message: string }>(
      `/api/planner/entries/by-meal/${mealId}`,
      {
        method: "DELETE",
      },
      token
    ),

  // -------------------------------------------------------------------------
  // Planner Entry Methods (Weekly Menu)
  // -------------------------------------------------------------------------

  /**
   * Get all planner entries with hydrated meal data
   * @param token - Optional auth token for authenticated requests
   */
  getEntries: (token?: string | null): Promise<PlannerEntryResponseDTO[]> =>
    fetchApi<PlannerEntryResponseDTO[]>("/api/planner/entries", undefined, token),

  /**
   * Add a meal to the planner (creates a PlannerEntry)
   * @param mealId - Meal ID
   * @param token - Optional auth token for authenticated requests
   */
  addToPlanner: (mealId: number, token?: string | null): Promise<PlannerEntryResponseDTO> =>
    fetchApi<PlannerEntryResponseDTO>(
      `/api/planner/entries/${mealId}`,
      {
        method: "POST",
      },
      token
    ),

  /**
   * Remove a planner entry by entry ID (meal persists)
   * @param entryId - Planner entry ID
   * @param token - Optional auth token for authenticated requests
   */
  removeEntry: (entryId: number, token?: string | null): Promise<{ message: string }> =>
    fetchApi<{ message: string }>(
      `/api/planner/entries/${entryId}`,
      {
        method: "DELETE",
      },
      token
    ),

  /**
   * Mark a planner entry as complete (records recipe history)
   * @param entryId - Planner entry ID
   * @param token - Optional auth token for authenticated requests
   */
  markComplete: (entryId: number, token?: string | null): Promise<PlannerEntryResponseDTO> =>
    fetchApi<PlannerEntryResponseDTO>(
      `/api/planner/entries/${entryId}/complete`,
      {
        method: "POST",
      },
      token
    ),

  /**
   * Mark a planner entry as incomplete
   * @param entryId - Planner entry ID
   * @param token - Optional auth token for authenticated requests
   */
  markIncomplete: (entryId: number, token?: string | null): Promise<PlannerEntryResponseDTO> =>
    fetchApi<PlannerEntryResponseDTO>(
      `/api/planner/entries/${entryId}/incomplete`,
      {
        method: "POST",
      },
      token
    ),

  /**
   * Cycle the shopping mode of a planner entry: all -> produce_only -> none -> all
   * @param entryId - Planner entry ID
   * @param token - Optional auth token for authenticated requests
   */
  setShoppingMode: (entryId: number, shoppingMode: "all" | "produce_only" | "none", token?: string | null): Promise<PlannerEntryResponseDTO> =>
    fetchApi<PlannerEntryResponseDTO>(`/api/planner/entries/${entryId}/shopping-mode`, { method: "PUT", body: JSON.stringify({ shopping_mode: shoppingMode }) }, token),

  cycleShoppingMode: (entryId: number, token?: string | null): Promise<PlannerEntryResponseDTO> =>
    fetchApi<PlannerEntryResponseDTO>(
      `/api/planner/entries/${entryId}/cycle-shopping-mode`,
      {
        method: "POST",
      },
      token
    ),

  /**
   * Clear all completed planner entries
   * @param token - Optional auth token for authenticated requests
   */
  clearCompleted: (token?: string | null): Promise<{ message: string }> =>
    fetchApi<{ message: string }>(
      "/api/planner/clear-completed",
      {
        method: "DELETE",
      },
      token
    ),

  /**
   * Reorder planner entries by providing entry IDs in desired order
   * @param entryIds - Array of entry IDs in desired order
   * @param token - Optional auth token for authenticated requests
   */
  reorderEntries: (
    entryIds: number[],
    token?: string | null
  ): Promise<{ success: boolean; message: string }> =>
    fetchApi<{ success: boolean; message: string }>(
      "/api/planner/entries/reorder",
      {
        method: "PUT",
        body: JSON.stringify({ entry_ids: entryIds }),
      },
      token
    ),

  /**
   * Get cooking streak information
   * Sends user's timezone to ensure correct date calculations
   * @param token - Optional auth token for authenticated requests
   */
  getStreak: (token?: string | null): Promise<CookingStreakDTO> => {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return fetchApi<CookingStreakDTO>(
      `/api/planner/streak?tz=${encodeURIComponent(tz)}`,
      undefined,
      token
    );
  },
};
