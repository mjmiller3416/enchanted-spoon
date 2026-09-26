import { recipeApi, uploadApi } from "@/lib/api";
import { ApiError } from "@/lib/api/base";
import type { RecipeCreateDTO } from "@/types/recipe";

type ImageSource = File | string | null;
type SavedImage = { source: ImageSource; path: string };
export interface RecipeSaveCheckpoint {
  id?: number;
  createUncertain?: boolean;
  reference?: SavedImage;
  banner?: SavedImage;
}

export class RecipeCreateUncertainError extends Error {
  constructor() {
    super("The save response was lost. Check your recipe library before trying to create this recipe again.");
    this.name = "RecipeCreateUncertainError";
  }
}

/** The checkpoint belongs to the open editor and survives partial failures.
 * A retry updates the existing record and reuses already uploaded images. */
export async function saveRecipeDraft({ checkpoint, payload, reference, banner, originalReference, originalBanner, token }: {
  checkpoint: RecipeSaveCheckpoint;
  payload: RecipeCreateDTO;
  reference: ImageSource;
  banner: ImageSource;
  originalReference: string | null;
  originalBanner: string | null;
  token: string | null;
}): Promise<number> {
  if (!checkpoint.id) {
    if (checkpoint.createUncertain) throw new RecipeCreateUncertainError();
    try {
      const created = await recipeApi.create(payload, token);
      if (!Number.isInteger(created.id) || created.id <= 0) throw new Error("Missing recipe ID");
      checkpoint.id = created.id;
    } catch (error) {
      // A timeout can occur after the server committed. Do not silently replay it.
      if (error instanceof ApiError && error.status >= 400 && error.status < 500 && error.status !== 408) throw error;
      checkpoint.createUncertain = true;
      throw new RecipeCreateUncertainError();
    }
  }
  const id = checkpoint.id;
  async function imagePath(kind: "reference" | "banner", source: ImageSource, original: string | null) {
    if (!source) return original;
    const previous = checkpoint[kind];
    if (previous?.source === source) return previous.path;
    const result = typeof source === "string"
      ? await uploadApi.uploadBase64Image(source, id, kind, token)
      : await uploadApi.uploadRecipeImage(source, id, kind, token);
    if (!result.success || !result.path) throw new Error(`The ${kind} image could not be uploaded.`);
    checkpoint[kind] = { source, path: result.path };
    return result.path;
  }
  const referencePath = await imagePath("reference", reference, originalReference);
  const bannerPath = await imagePath("banner", banner, originalBanner);
  await recipeApi.update(id, {
    ...payload,
    reference_image_path: referencePath,
    banner_image_path: bannerPath,
  }, token);
  return id;
}
