import { recipeApi, uploadApi } from "@/lib/api";
import type { RecipeCreateDTO } from "@/types/recipe";

type ImageSource = File | string | null;
type SavedImage = { source: ImageSource; path: string };
export interface RecipeSaveCheckpoint {
  id?: number;
  reference?: SavedImage;
  banner?: SavedImage;
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
    const created = await recipeApi.create(payload, token);
    checkpoint.id = created.id;
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
