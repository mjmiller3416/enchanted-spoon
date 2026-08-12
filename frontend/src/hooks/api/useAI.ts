"use client";

import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  mealSuggestionsApi,
  imageGenerationApi,
  nutritionEstimationApi,
  recipeGenerationApi,
  AssistantApi,
} from "@/lib/api";
import type {
  ImageGenerationType,
  MealSuggestionsRequestDTO,
  NutritionEstimationRequestDTO,
  RecipeGenerationRequestDTO,
  AssistantMessage,
} from "@/types/ai";

// ============================================================================
// MUTATION HOOKS
// ============================================================================

/**
 * Get AI-powered meal suggestions (side dishes + cooking tip) for a meal.
 * Uses mutation because each call generates new suggestions.
 */
export function useMealSuggestions() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async (request: MealSuggestionsRequestDTO) => {
      const token = await getToken();
      return mealSuggestionsApi.getSuggestions(request, token);
    },
  });
}

/**
 * Generate an AI image for a recipe.
 * Returns base64-encoded image data.
 */
export function useGenerateImage() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async ({
      recipeName,
      customPrompt,
      imageType,
    }: {
      recipeName: string;
      customPrompt?: string;
      imageType?: ImageGenerationType;
    }) => {
      const token = await getToken();
      return imageGenerationApi.generate(recipeName, customPrompt, token, imageType);
    },
  });
}

/**
 * Generate a banner image from a reference image.
 * Returns base64-encoded banner image data (21:9 aspect ratio).
 */
export function useGenerateBanner() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async ({
      recipeName,
      referenceImageData,
    }: {
      recipeName: string;
      referenceImageData: string;
    }) => {
      const token = await getToken();
      return imageGenerationApi.generateBanner(recipeName, referenceImageData, token);
    },
  });
}

/**
 * Send a message to the Genie AI assistant.
 * Supports conversation history for context.
 * May return chat response, recipe suggestions, or a generated recipe.
 */
export function useAssistantChat() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async ({
      message,
      conversationHistory,
    }: {
      message: string;
      conversationHistory?: AssistantMessage[];
    }) => {
      const token = await getToken();
      return AssistantApi.chat(message, conversationHistory, token);
    },
  });
}

/**
 * Ask the Genie a question.
 * Alias for useAssistantChat - uses the same endpoint.
 * Supports conversation history for context.
 */
export function useAssistantAsk() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async ({
      message,
      conversationHistory,
    }: {
      message: string;
      conversationHistory?: AssistantMessage[];
    }) => {
      const token = await getToken();
      return AssistantApi.ask(message, conversationHistory, token);
    },
  });
}

/**
 * Estimate nutrition facts for a recipe using AI.
 * Requires recipe name, ingredients, and optional servings.
 */
export function useEstimateNutrition() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async (request: NutritionEstimationRequestDTO) => {
      const token = await getToken();
      return nutritionEstimationApi.estimate(request, token);
    },
  });
}

/**
 * Generate a complete recipe from a text prompt using AI.
 * Returns recipe data with optional nutrition facts and images.
 */
export function useRecipeGenerate() {
  const { getToken } = useAuth();

  return useMutation({
    mutationFn: async (request: RecipeGenerationRequestDTO) => {
      const token = await getToken();
      return recipeGenerationApi.generate(request, token);
    },
  });
}

