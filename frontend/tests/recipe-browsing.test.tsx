import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RecipeImage } from "@/components/recipe/RecipeImage";
import { RecipeGrid } from "@/components/recipe/browser/RecipeGrid";
import { compareRecipes } from "@/lib/recipe-sorting";
import type { RecipeCardData } from "@/types/recipe";

vi.mock("@/components/recipe/RecipeCard", () => ({
  RecipeCard: ({ recipe }: { recipe: RecipeCardData }) => <span data-testid="recipe">{recipe.name}</span>,
  RecipeCardGrid: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
const recipe = (id: number, date?: string) => ({ id, name: `Recipe ${id}`, createdAt: date } as RecipeCardData);

describe("recipe browsing", () => {
  it("sorts by actual dates rather than imported record IDs, keeping missing dates last", () => {
    const data = [recipe(999, "2020-01-01"), recipe(1, "2026-01-01"), recipe(2)];
    expect(data.sort((a, b) => compareRecipes(a, b, "createdAt", "desc")).map(r => r.id)).toEqual([1, 999, 2]);
  });
  it("recovers after a failed image is replaced", () => {
    const view = render(<RecipeImage src="/old.jpg" alt="Recipe" />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.queryByRole("img")).toBeNull();
    view.rerender(<RecipeImage src="/new.jpg" alt="Recipe" />);
    expect(screen.getByRole("img").getAttribute("src")).toBe("/new.jpg");
    expect(screen.getByRole("img").getAttribute("loading")).toBe("lazy");
  });
  it("bounds mounted cards for a 5,000 recipe collection and reaches the next page", () => {
    Element.prototype.scrollIntoView = vi.fn();
    render(<RecipeGrid recipes={Array.from({ length: 5000 }, (_, i) => recipe(i))} hasActiveFilters={false} onRecipeClick={vi.fn()} onFavoriteToggle={vi.fn()} onClearFilters={vi.fn()} />);
    expect(screen.getAllByTestId("recipe")).toHaveLength(24);
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Recipe 24")).toBeTruthy();
    expect(screen.queryByText("Recipe 0")).toBeNull();
    expect(screen.getAllByTestId("recipe")).toHaveLength(24);
  });
});
