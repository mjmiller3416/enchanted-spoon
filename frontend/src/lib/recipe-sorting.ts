import type { RecipeCardData } from "@/types/recipe";

export function compareRecipes(a: RecipeCardData, b: RecipeCardData, sort: "alphabetical" | "cookTime" | "createdAt", direction: "asc" | "desc") {
  let value: number;
  if (sort === "alphabetical") value = a.name.localeCompare(b.name);
  else if (sort === "cookTime") value = (a.totalTime ?? 0) - (b.totalTime ?? 0);
  else {
    const aDate = Date.parse(a.createdAt ?? "");
    const bDate = Date.parse(b.createdAt ?? "");
    // Legacy records without dates stay last in either direction.
    if (!Number.isFinite(aDate) && Number.isFinite(bDate)) return 1;
    if (Number.isFinite(aDate) && !Number.isFinite(bDate)) return -1;
    value = Number.isFinite(aDate) && Number.isFinite(bDate) ? aDate - bDate : 0;
  }
  return (direction === "asc" ? value : -value) || String(a.id).localeCompare(String(b.id), undefined, { numeric: true });
}
