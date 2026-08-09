import type {
  ImageGenerationResponseDTO,
  ImageGenerationType,
  BannerGenerationResponseDTO,
  CookingTipResponseDTO,
  AssistantMessage,
  AssistantResponseDTO,
  MealSuggestionsRequestDTO,
  MealSuggestionsResponseDTO,
  NutritionEstimationRequestDTO,
  NutritionEstimationResponseDTO,
  RecipeGenerationRequestDTO,
  RecipeGenerationResponseDTO,
  RecipeImportRequestDTO,
  RecipeImportResponseDTO,
} from "@/types/ai";
import { AI_TIMEOUT_MS, fetchApi } from "./base";

export const imageGenerationApi = {
  /**
   * Generate an AI image for a recipe based on its name
   * @param recipeName - The name of the recipe to generate an image for
   * @param customPrompt - Optional custom prompt template (must include {recipe_name})
   * @param token - Optional auth token for authenticated requests
   * @returns Response with base64 encoded image data on success
   */
  generate: (
    recipeName: string,
    customPrompt?: string,
    token?: string | null,
    imageType?: ImageGenerationType
  ): Promise<ImageGenerationResponseDTO> =>
    fetchApi<ImageGenerationResponseDTO>(
      "/api/ai/image-generation",
      {
        method: "POST",
        body: JSON.stringify({
          recipe_name: recipeName,
          ...(customPrompt && { custom_prompt: customPrompt }),
          ...(imageType && { image_type: imageType }),
        }),
      },
      token,
      AI_TIMEOUT_MS
    ),

  /**
   * Generate a banner image from a reference image
   * @param recipeName - The name of the recipe
   * @param referenceImageData - Base64 encoded reference image
   * @param token - Optional auth token for authenticated requests
   * @returns Response with base64 encoded banner image data on success
   */
  generateBanner: (
    recipeName: string,
    referenceImageData: string,
    token?: string | null
  ): Promise<BannerGenerationResponseDTO> =>
    fetchApi<BannerGenerationResponseDTO>(
      "/api/ai/image-generation/banner",
      {
        method: "POST",
        body: JSON.stringify({
          recipe_name: recipeName,
          reference_image_data: referenceImageData,
        }),
      },
      token,
      AI_TIMEOUT_MS
    ),
};

export const cookingTipApi = {
  /**
   * Get a random cooking tip from AI
   * @param token - Optional auth token for authenticated requests
   * @returns Response with cooking tip on success
   */
  getTip: (token?: string | null): Promise<CookingTipResponseDTO> =>
    fetchApi<CookingTipResponseDTO>("/api/ai/cooking-tip", undefined, token, AI_TIMEOUT_MS),
};

export const mealSuggestionsApi = {
  /**
   * Get AI-powered side dish suggestions and cooking tip for a meal
   * @param request The meal details to generate suggestions for
   * @param token - Optional auth token for authenticated requests
   * @returns Response with suggestions on success
   */
  getSuggestions: (
    request: MealSuggestionsRequestDTO,
    token?: string | null
  ): Promise<MealSuggestionsResponseDTO> =>
    fetchApi<MealSuggestionsResponseDTO>(
      "/api/ai/meal-suggestions",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      token,
      AI_TIMEOUT_MS
    ),
};

export const nutritionEstimationApi = {
  estimate: (
    request: NutritionEstimationRequestDTO,
    token?: string | null
  ): Promise<NutritionEstimationResponseDTO> =>
    fetchApi<NutritionEstimationResponseDTO>(
      "/api/ai/nutrition-estimation",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      token,
      AI_TIMEOUT_MS
    ),
};

export const recipeGenerationApi = {
  /**
   * Generate a complete recipe from a text prompt using AI.
   * @param request - Prompt, optional preferences, and feature flags.
   * @param token - Optional auth token for authenticated requests.
   * @returns Response with generated recipe, optional nutrition and images.
   */
  generate: (
    request: RecipeGenerationRequestDTO,
    token?: string | null
  ): Promise<RecipeGenerationResponseDTO> =>
    fetchApi<RecipeGenerationResponseDTO>(
      "/api/ai/wizard-generation",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      token,
      AI_TIMEOUT_MS
    ),
};

export const recipeImportApi = {
  /**
   * Import a recipe from a website URL.
   * @param request - The URL to import and whether to include the source photo.
   * @param token - Optional auth token for authenticated requests.
   * @returns Response with normalized recipe, site nutrition, and source image.
   */
  importFromUrl: (
    request: RecipeImportRequestDTO,
    token?: string | null
  ): Promise<RecipeImportResponseDTO> =>
    fetchApi<RecipeImportResponseDTO>(
      "/api/ai/recipe-import",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
      token,
      AI_TIMEOUT_MS
    ),
};

export const AssistantApi = {
  /**
   * Send a message to Meal Genie
   * AI decides whether to chat, suggest recipes, or generate a full recipe
   * @param message The user's message
   * @param conversationHistory Optional previous messages for context
   * @param token - Optional auth token for authenticated requests
   * @returns Response with AI-generated answer, optionally including recipe
   */
  chat: (
    message: string,
    conversationHistory?: AssistantMessage[],
    token?: string | null
  ): Promise<AssistantResponseDTO> =>
    fetchApi<AssistantResponseDTO>(
      "/api/ai/meal-genie/chat",
      {
        method: "POST",
        body: JSON.stringify({
          message,
          conversation_history: conversationHistory,
        }),
      },
      token,
      AI_TIMEOUT_MS
    ),

  /**
   * Send a message to Meal Genie (alias for chat)
   * @deprecated Use chat() instead
   * @param message The user's message
   * @param conversationHistory Optional previous messages for context
   * @param token - Optional auth token for authenticated requests
   */
  ask: (
    message: string,
    conversationHistory?: AssistantMessage[],
    token?: string | null
  ): Promise<AssistantResponseDTO> =>
    fetchApi<AssistantResponseDTO>(
      "/api/ai/meal-genie/chat",
      {
        method: "POST",
        body: JSON.stringify({
          message,
          conversation_history: conversationHistory,
        }),
      },
      token,
      AI_TIMEOUT_MS
    ),

};
