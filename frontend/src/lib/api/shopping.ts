import type {
  ShoppingListResponseDTO,
  ShoppingItemResponseDTO,
  ShoppingListGenerationResultDTO,
  ManualItemCreateDTO,
  ShoppingItemUpdateDTO,
  ShoppingListFilterDTO,
  ShoppingListGenerationDTO,
  ShoppingNotesDTO,
} from "@/types/shopping";
import type { IngredientBreakdownDTO } from "@/types/recipe";
import type { BulkOperationResultDTO } from "@/types/common";
import { fetchApi, buildQueryString } from "./base";

export const shoppingApi = {
  /**
   * Get shopping list with optional filters.
   * Shopping list is automatically synced when planner changes occur.
   * @param filters - Optional filter parameters
   * @param token - Optional auth token for authenticated requests
   */
  getList: (
    filters?: ShoppingListFilterDTO,
    token?: string | null
  ): Promise<ShoppingListResponseDTO> => {
    const query = filters ? buildQueryString(filters as Record<string, unknown>) : "";
    return fetchApi<ShoppingListResponseDTO>(`/api/shopping${query}`, undefined, token);
  },

  /**
   * Get a single shopping item
   * @param id - Shopping item ID
   * @param token - Optional auth token for authenticated requests
   */
  getItem: (id: number, token?: string | null): Promise<ShoppingItemResponseDTO> =>
    fetchApi<ShoppingItemResponseDTO>(`/api/shopping/items/${id}`, undefined, token),

  /**
   * Add a manual item
   * @param data - Manual item data
   * @param token - Optional auth token for authenticated requests
   */
  addItem: (data: ManualItemCreateDTO, token?: string | null): Promise<ShoppingItemResponseDTO> =>
    fetchApi<ShoppingItemResponseDTO>(
      "/api/shopping/items",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token
    ),

  /**
   * Update a shopping item
   * @param id - Shopping item ID
   * @param data - Item data to update
   * @param token - Optional auth token for authenticated requests
   */
  updateItem: (
    id: number,
    data: ShoppingItemUpdateDTO,
    token?: string | null
  ): Promise<ShoppingItemResponseDTO> =>
    fetchApi<ShoppingItemResponseDTO>(
      `/api/shopping/items/${id}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
      token
    ),

  /**
   * Toggle item have status
   * @param id - Shopping item ID
   * @param token - Optional auth token for authenticated requests
   */
  toggleItem: (id: number, token?: string | null): Promise<{ success: boolean }> =>
    fetchApi<{ success: boolean }>(
      `/api/shopping/items/${id}/toggle`,
      {
        method: "PATCH",
      },
      token
    ),

  /**
   * Toggle item flagged status
   * @param id - Shopping item ID
   * @param token - Optional auth token for authenticated requests
   */
  toggleFlagged: (id: number, token?: string | null): Promise<{ success: boolean; flagged: boolean }> =>
    fetchApi<{ success: boolean; flagged: boolean }>(
      `/api/shopping/items/${id}/toggle-flag`,
      {
        method: "PATCH",
      },
      token
    ),

  /**
   * Delete a shopping item
   * @param id - Shopping item ID
   * @param token - Optional auth token for authenticated requests
   */
  deleteItem: (id: number, token?: string | null): Promise<void> =>
    fetchApi<void>(`/api/shopping/items/${id}`, { method: "DELETE" }, token),

  /**
   * Generate shopping list from recipes
   * @param data - Generation parameters
   * @param token - Optional auth token for authenticated requests
   */
  generate: (
    data: ShoppingListGenerationDTO,
    token?: string | null
  ): Promise<ShoppingListGenerationResultDTO> =>
    fetchApi<ShoppingListGenerationResultDTO>(
      "/api/shopping/generate",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token
    ),

  /**
   * Generate shopping list from active planner entries.
   * @deprecated Shopping list is now automatically synced when planner changes.
   * This method is kept for backwards compatibility but is no longer necessary.
   * @param token - Optional auth token for authenticated requests
   */
  generateFromPlanner: (token?: string | null): Promise<ShoppingListGenerationResultDTO> =>
    fetchApi<ShoppingListGenerationResultDTO>(
      "/api/shopping/generate-from-planner",
      {
        method: "POST",
      },
      token
    ),

  /**
   * Clear entire shopping list
   * @param token - Optional auth token for authenticated requests
   */
  clear: (token?: string | null): Promise<BulkOperationResultDTO> =>
    fetchApi<BulkOperationResultDTO>(
      "/api/shopping/clear",
      {
        method: "DELETE",
      },
      token
    ),

  /**
   * Clear only manual items
   * @param token - Optional auth token for authenticated requests
   */
  clearManual: (token?: string | null): Promise<BulkOperationResultDTO> =>
    fetchApi<BulkOperationResultDTO>(
      "/api/shopping/clear-manual",
      {
        method: "DELETE",
      },
      token
    ),

  /**
   * Clear completed items
   * @param token - Optional auth token for authenticated requests
   */
  clearCompleted: (token?: string | null): Promise<{ message: string; deleted_count: number }> =>
    fetchApi<{ message: string; deleted_count: number }>(
      "/api/shopping/clear-completed",
      { method: "DELETE" },
      token
    ),

  /**
   * Bulk update item status
   * @param itemUpdates - Map of item IDs to their new have status
   * @param token - Optional auth token for authenticated requests
   */
  bulkUpdate: (
    itemUpdates: Record<number, boolean>,
    token?: string | null
  ): Promise<BulkOperationResultDTO> =>
    fetchApi<BulkOperationResultDTO>(
      "/api/shopping/bulk-update",
      {
        method: "PATCH",
        body: JSON.stringify({ item_updates: itemUpdates }),
      },
      token
    ),

  /**
   * Get ingredient breakdown
   * @param recipeIds - Array of recipe IDs
   * @param token - Optional auth token for authenticated requests
   */
  getBreakdown: (recipeIds: number[], token?: string | null): Promise<IngredientBreakdownDTO[]> =>
    fetchApi<IngredientBreakdownDTO[]>(
      `/api/shopping/breakdown?recipe_ids=${recipeIds.join(",")}`,
      undefined,
      token
    ),

  /**
   * Get the shopping list notes
   * @param token - Optional auth token for authenticated requests
   */
  getNotes: (token?: string | null): Promise<ShoppingNotesDTO> =>
    fetchApi<ShoppingNotesDTO>("/api/shopping/notes", undefined, token),

  /**
   * Replace the shopping list notes
   * @param content - Full notes text
   * @param token - Optional auth token for authenticated requests
   */
  saveNotes: (content: string, token?: string | null): Promise<ShoppingNotesDTO> =>
    fetchApi<ShoppingNotesDTO>(
      "/api/shopping/notes",
      {
        method: "PUT",
        body: JSON.stringify({ content }),
      },
      token
    ),
};
