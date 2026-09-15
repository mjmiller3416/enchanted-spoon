import { beforeEach, expect, it, vi } from "vitest";
import { saveRecipeDraft, type RecipeSaveCheckpoint } from "@/lib/recipe-save";

const api = vi.hoisted(() => ({ create: vi.fn(), update: vi.fn(), upload: vi.fn() }));
vi.mock("@/lib/api", () => ({ recipeApi: { create: api.create, update: api.update }, uploadApi: { uploadBase64Image: api.upload, uploadRecipeImage: api.upload } }));
beforeEach(() => { vi.resetAllMocks(); api.create.mockResolvedValue({ id: 42 }); api.update.mockResolvedValue({ id: 42 }); });
const options = (checkpoint: RecipeSaveCheckpoint) => ({ checkpoint, payload: { recipe_name: "Soup", recipe_category: "Dinner" }, reference: "reference-data", banner: "banner-data", originalReference: null, originalBanner: null, token: "test" });

it("resumes after the second image fails without recreating or reuploading the first", async () => {
  const checkpoint: RecipeSaveCheckpoint = {};
  api.upload.mockResolvedValueOnce({ success: true, path: "/reference" }).mockRejectedValueOnce(new Error("offline"));
  await expect(saveRecipeDraft(options(checkpoint))).rejects.toThrow("offline");
  expect(checkpoint.id).toBe(42);
  api.upload.mockResolvedValueOnce({ success: true, path: "/banner" });
  expect(await saveRecipeDraft(options(checkpoint))).toBe(42);
  expect(api.create).toHaveBeenCalledTimes(1);
  expect(api.upload).toHaveBeenCalledTimes(3);
  expect(api.update).toHaveBeenCalledWith(42, expect.objectContaining({ reference_image_path: "/reference", banner_image_path: "/banner" }), "test");
});

it("retries a failed final patch against the same record and uses the latest edits", async () => {
  const checkpoint: RecipeSaveCheckpoint = {};
  api.upload.mockResolvedValue({ success: true, path: "/image" });
  api.update.mockRejectedValueOnce(new Error("patch failed")).mockResolvedValueOnce({ id: 42 });
  await expect(saveRecipeDraft(options(checkpoint))).rejects.toThrow("patch failed");
  await saveRecipeDraft({ ...options(checkpoint), payload: { recipe_name: "Updated soup", recipe_category: "Dinner" } });
  expect(api.create).toHaveBeenCalledTimes(1);
  expect(api.upload).toHaveBeenCalledTimes(2);
  expect(api.update).toHaveBeenLastCalledWith(42, expect.objectContaining({ recipe_name: "Updated soup" }), "test");
});

it("does not report an edit as saved when an image fails", async () => {
  api.upload.mockRejectedValue(new Error("upload failed"));
  await expect(saveRecipeDraft(options({ id: 12 }))).rejects.toThrow("upload failed");
  expect(api.create).not.toHaveBeenCalled();
  expect(api.update).not.toHaveBeenCalled();
});

it("uploads a changed image instead of reusing its previous checkpoint", async () => {
  const checkpoint: RecipeSaveCheckpoint = { id: 42, reference: { source: "old", path: "/old" } };
  api.upload.mockResolvedValue({ success: true, path: "/new" });
  await saveRecipeDraft({ ...options(checkpoint), banner: null });
  expect(api.upload).toHaveBeenCalledTimes(1);
  expect(api.update).toHaveBeenCalledWith(42, expect.objectContaining({ reference_image_path: "/new" }), "test");
});
