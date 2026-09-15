import type {
  RecipeResponseDTO,
  RecipeCardDTO,
  RecipeFilterDTO,
  RecipeCreateDTO,
  RecipeUpdateDTO,
} from "@/types/recipe";
import { fetchApi, buildQueryString } from "./base";

export const recipeApi = {
  deletionImpact: (id: number, token?: string | null): Promise<{ meals_to_delete: { id: number; meal_name: string }[]; meals_to_update: { id: number; meal_name: string }[]; total_affected: number }> =>
    fetchApi(`/api/recipes/${id}/deletion-impact`, undefined, token),
  /**
   * List recipes with optional filters
   * @param filters - Optional filter parameters
   * @param token - Optional auth token for authenticated requests
   */
  list: (filters?: Partial<RecipeFilterDTO>, token?: string | null): Promise<RecipeResponseDTO[]> => {
    const query = filters ? buildQueryString(filters) : "";
    return fetchApi<RecipeResponseDTO[]>(`/api/recipes${query}`, undefined, token);
  },

  /**
   * List recipes as lightweight cards
   * @param filters - Optional filter parameters
   * @param token - Optional auth token for authenticated requests
   */
  listCards: (
    filters?: {
      recipe_category?: string;
      meal_type?: string;
      favorites_only?: boolean;
      search_term?: string;
      limit?: number;
    },
    token?: string | null
  ): Promise<RecipeCardDTO[]> => {
    const query = filters ? buildQueryString(filters) : "";
    return fetchApi<RecipeCardDTO[]>(`/api/recipes/cards${query}`, undefined, token);
  },

  /**
   * Get a single recipe by ID
   * @param id - Recipe ID
   * @param token - Optional auth token for authenticated requests
   */
  get: (id: number, token?: string | null): Promise<RecipeResponseDTO> =>
    fetchApi<RecipeResponseDTO>(`/api/recipes/${id}`, undefined, token),

  /**
   * Create a new recipe
   * @param data - Recipe data
   * @param token - Optional auth token for authenticated requests
   */
  create: (data: RecipeCreateDTO, token?: string | null): Promise<RecipeResponseDTO> =>
    fetchApi<RecipeResponseDTO>(
      "/api/recipes",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
      token
    ),

  /**
   * Update an existing recipe
   * @param id - Recipe ID
   * @param data - Recipe data to update
   * @param token - Optional auth token for authenticated requests
   */
  update: (id: number, data: RecipeUpdateDTO, token?: string | null): Promise<RecipeResponseDTO> =>
    fetchApi<RecipeResponseDTO>(
      `/api/recipes/${id}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
      token
    ),

  /**
   * Delete a recipe
   * @param id - Recipe ID
   * @param token - Optional auth token for authenticated requests
   */
  delete: (id: number, token?: string | null): Promise<void> =>
    fetchApi<void>(`/api/recipes/${id}`, { method: "DELETE" }, token),

  /**
   * Toggle favorite status
   * @param id - Recipe ID
   * @param token - Optional auth token for authenticated requests
   */
  toggleFavorite: (id: number, token?: string | null): Promise<RecipeResponseDTO> =>
    fetchApi<RecipeResponseDTO>(
      `/api/recipes/${id}/favorite`,
      {
        method: "POST",
      },
      token
    ),

  /**
   * Get unique categories
   * @param token - Optional auth token for authenticated requests
   */
  getCategories: (token?: string | null): Promise<string[]> =>
    fetchApi<string[]>("/api/recipes/categories", undefined, token),

  /**
   * Get unique meal types
   * @param token - Optional auth token for authenticated requests
   */
  getMealTypes: (token?: string | null): Promise<string[]> =>
    fetchApi<string[]>("/api/recipes/meal-types", undefined, token),
};
