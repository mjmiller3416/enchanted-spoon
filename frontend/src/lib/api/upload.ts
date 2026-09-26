import { API_BASE, toApiError } from "./base";

export const uploadApi = {
  /**
   * Upload a recipe image to Cloudinary
   * @param file - The image file to upload
   * @param recipeId - The recipe ID (used to organize the file)
   * @param imageType - Either "reference" (thumbnail) or "banner" (hero image)
   * @param token - Optional auth token for authenticated requests
   * @returns The path to the uploaded image
   */
  uploadRecipeImage: async (
    file: File,
    recipeId: number,
    imageType: "reference" | "banner" = "reference",
    token?: string | null
  ): Promise<{ success: boolean; path: string; filename: string }> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("recipeId", recipeId.toString());
    formData.append("imageType", imageType);

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      throw await toApiError(response, "Failed to upload image");
    }

    return response.json();
  },

  /**
   * Upload a base64 encoded image to Cloudinary
   * Used for AI-generated images
   * @param imageData - Base64 encoded image data
   * @param recipeId - The recipe ID (used to organize the file)
   * @param imageType - Either "reference" (thumbnail) or "banner" (hero image)
   * @param token - Optional auth token for authenticated requests
   * @returns The path to the uploaded image
   */
  uploadBase64Image: async (
    imageData: string,
    recipeId: number,
    imageType: "reference" | "banner" = "reference",
    token?: string | null
  ): Promise<{ success: boolean; path: string; filename: string }> => {
    const formData = new FormData();
    formData.append("image_data", imageData);
    formData.append("recipeId", recipeId.toString());
    formData.append("imageType", imageType);

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/upload/base64`, {
      method: "POST",
      body: formData,
      headers,
    });

    if (!response.ok) {
      throw await toApiError(response, "Failed to upload image");
    }

    return response.json();
  },
};
