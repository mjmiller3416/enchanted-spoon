import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { RecipeWizardView } from "@/app/(app)/recipes/_components/wizard/RecipeWizardView";
import { handleNativeBackButton } from "@/lib/native/back-button";
import type { RecipeResponseDTO } from "@/types/recipe";

if (!HTMLElement.prototype.hasPointerCapture) {
  HTMLElement.prototype.hasPointerCapture = () => false;
}
HTMLElement.prototype.setPointerCapture ??= () => {};
HTMLElement.prototype.releasePointerCapture ??= () => {};
HTMLElement.prototype.scrollIntoView ??= () => {};

const api = vi.hoisted(() => ({
  get: vi.fn(),
  update: vi.fn(),
  listIngredients: vi.fn(async () => []),
  listCategories: vi.fn(async () => []),
  getSettings: vi.fn(async () => ({})),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ userId: "user", isLoaded: true, isSignedIn: true, getToken: async () => "token" }),
  useUser: () => ({ isLoaded: true, isSignedIn: true, user: null }),
  useClerk: () => ({ signOut: async () => undefined }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  usePathname: () => "/recipes",
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    recipeApi: { ...actual.recipeApi, get: api.get, update: api.update },
    ingredientApi: { ...actual.ingredientApi, list: api.listIngredients },
    categoryApi: { ...actual.categoryApi, list: api.listCategories },
    settingsApi: { ...actual.settingsApi, get: api.getSettings, update: async (patch: unknown) => patch },
  };
});

const recipe: RecipeResponseDTO = {
  id: 1,
  recipe_name: "Tomato Soup",
  recipe_category: "Soup",
  meal_type: "dinner",
  diet_pref: "none",
  description: "Warm bowl",
  prep_time: 10,
  cook_time: 20,
  servings: 4,
  difficulty: "Easy",
  directions: "Simmer",
  notes: "",
  reference_image_path: null,
  banner_image_path: null,
  source_url: null,
  total_time: 30,
  is_favorite: false,
  is_ai_generated: false,
  created_at: null,
  ingredients: [{ id: 1, ingredient_name: "Tomato", ingredient_category: "Produce", quantity: 2, unit: "cups" }],
  group_ids: [],
  nutrition_facts: null,
};

function Editor() {
  const [open, setOpen] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>Reopen editor</button>
      <RecipeWizardView open={open} onOpenChange={setOpen} mode="edit" recipeId={1} />
    </>
  );
}

async function editTitleAndExit(): Promise<HTMLElement> {
  const title = await screen.findByDisplayValue("Tomato Soup");
  fireEvent.input(title, { target: { value: "Tomato Soup Revised" } });
  expect((title as HTMLInputElement).value).toBe("Tomato Soup Revised");
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  const dialog = await screen.findByRole("alertdialog");
  expect(dialog.textContent).toContain("Discard changes?");
  expect(dialog.textContent).not.toMatch(/\bAI\b/);
  const keep = screen.getByRole("button", { name: /keep editing/i });
  const discard = screen.getByRole("button", { name: "Discard" });
  const footer = keep.closest("[data-slot=alert-dialog-footer]");
  expect(footer).toBeTruthy();
  expect(footer?.className).toContain("flex-row");
  expect(footer?.className).not.toContain("flex-col-reverse");
  expect(footer?.className).not.toMatch(/(?:^|\s)hidden(?:\s|$)/);
  expect(keep.className).toContain("border");
  expect(discard.className).toContain("bg-destructive");
  expect(keep.compareDocumentPosition(discard) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  const content = document.querySelector("[data-slot=alert-dialog-content]");
  expect(content?.className).toContain("overflow-y-auto");
  expect(content?.className).toContain("safe-area-inset-bottom");
  const viewport = document.querySelector("[data-slot=alert-dialog-viewport]");
  expect(viewport?.className).toContain("safe-area-inset-bottom");
  expect(viewport?.className).not.toContain("backdrop-blur");
  return dialog;
}

async function stillEditing() {
  await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
  expect(screen.getByRole("heading", { name: "Recipe Basics" })).toBeTruthy();
  expect(screen.getByDisplayValue("Tomato Soup Revised")).toBeTruthy();
}

beforeEach(() => {
  api.get.mockResolvedValue(recipe);
  api.update.mockResolvedValue(recipe);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("keeps the edited recipe when Keep editing is pressed", async () => {
  render(<QueryProvider><Editor /></QueryProvider>);
  await editTitleAndExit();
  fireEvent.click(screen.getByRole("button", { name: /keep editing/i }));
  await stillEditing();
  expect(api.update).not.toHaveBeenCalled();
});

it("discards the draft and leaves the editor", async () => {
  render(<QueryProvider><Editor /></QueryProvider>);
  await editTitleAndExit();
  fireEvent.click(screen.getByRole("button", { name: "Discard" }));
  await waitFor(() => expect(screen.queryByRole("heading", { name: "Recipe Basics" })).toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "Reopen editor" }));
  expect(await screen.findByRole("heading", { name: "Choose Method" })).toBeTruthy();
  expect(screen.queryByDisplayValue("Tomato Soup Revised")).toBeNull();
  expect(api.update).not.toHaveBeenCalled();
});

it("does not discard when Escape or the overlay is pressed", async () => {
  render(<QueryProvider><Editor /></QueryProvider>);
  await editTitleAndExit();
  fireEvent.keyDown(document, { key: "Escape", code: "Escape" });
  await stillEditing();

  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  await screen.findByRole("alertdialog");
  const viewport = document.querySelector("[data-slot=alert-dialog-viewport]");
  expect(viewport).toBeTruthy();
  fireEvent.pointerDown(viewport as Element, { button: 0, pointerId: 1, pointerType: "touch" });
  await stillEditing();
  expect(api.update).not.toHaveBeenCalled();
});

it("closes the discard prompt on the hardware back button without discarding", async () => {
  const back = vi.spyOn(window.history, "back").mockImplementation(() => {});
  render(<QueryProvider><Editor /></QueryProvider>);
  await editTitleAndExit();
  expect(handleNativeBackButton({ canGoBack: true })).toBe("dismiss-dialog");
  expect(back).not.toHaveBeenCalled();
  await stillEditing();
  expect(api.update).not.toHaveBeenCalled();
  back.mockRestore();
});
