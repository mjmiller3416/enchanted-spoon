import "./print-styles.css";
import Image from "next/image";
import { getRecipeCardUrl } from "@/lib/imageUtils";
import { formatQuantity } from "@/lib/utils";
import { formatTime, sortCategoryEntries } from "../recipe-utils";
import type { PrintOptions } from "./PrintPreviewDialog";
import type { RecipeResponseDTO, NutritionFactsResponseDTO } from "@/types/recipe";

interface RecipePrintLayoutProps {
  recipe: RecipeResponseDTO;
  directions: string[];
  groupedIngredients: Map<string, RecipeResponseDTO["ingredients"]>;
  printOptions: PrintOptions;
}

const NUTRITION_PRINT_ROWS: {
  key: keyof NutritionFactsResponseDTO;
  label: string;
  unit: string;
}[] = [
  { key: "calories", label: "Calories", unit: "kcal" },
  { key: "total_fat_g", label: "Total Fat", unit: "g" },
  { key: "saturated_fat_g", label: "Saturated Fat", unit: "g" },
  { key: "trans_fat_g", label: "Trans Fat", unit: "g" },
  { key: "cholesterol_mg", label: "Cholesterol", unit: "mg" },
  { key: "sodium_mg", label: "Sodium", unit: "mg" },
  { key: "total_carbs_g", label: "Total Carbohydrates", unit: "g" },
  { key: "dietary_fiber_g", label: "Dietary Fiber", unit: "g" },
  { key: "total_sugars_g", label: "Total Sugars", unit: "g" },
  { key: "protein_g", label: "Protein", unit: "g" },
];

const formatNutritionValue = (value: number | null | boolean): string => {
  if (value === null || typeof value === "boolean") return "—";
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
};

/**
 * Print-only layout component for recipes.
 * Hidden on screen, visible only during print.
 * Renders a clean, two-column format optimized for paper.
 */
export function RecipePrintLayout({
  recipe,
  directions,
  groupedIngredients,
  printOptions,
}: RecipePrintLayoutProps) {
  return (
    <div className="hidden p-6 print:block">
      {/* Wrap entire recipe to prevent page breaks */}
      <div className="print-recipe-content">
        {/* Header: Title and Meta */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold tracking-wide text-black uppercase">
              {recipe.recipe_name}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              {[recipe.meal_type, recipe.recipe_category, recipe.diet_pref, recipe.difficulty].filter(Boolean).join(" • ")}
            </p>
            {recipe.description && (
              <p className="mt-1 text-sm text-gray-700 italic">{recipe.description}</p>
            )}
          </div>
          {printOptions.showMeta && (
            <div className="text-sm text-right text-gray-700">
              <div className="flex items-center justify-end gap-1 mb-1">
                <span>{recipe.servings || "—"} servings</span>
              </div>
              <div className="flex items-center justify-end gap-1 mb-1">
                <span>Prep: {formatTime(recipe.prep_time)} · Cook: {formatTime(recipe.cook_time)}</span>
              </div>
              <div className="flex items-center justify-end gap-1">
                <span>Total: {formatTime(recipe.total_time)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Recipe Image */}
        {/* priority: the print layout is display:none on screen, so a lazy image
            never loads during browsing and races the print snapshot at print time.
            The Cloudinary resize keeps the fetch small (~150KB) vs multi-MB originals. */}
        {printOptions.showImage && recipe.reference_image_path && (
          <div className="mb-4">
            <Image
              src={getRecipeCardUrl(recipe.reference_image_path, 1200, 600) ?? recipe.reference_image_path}
              alt={recipe.recipe_name}
              width={800}
              height={192}
              className="object-cover w-full rounded-lg max-h-48"
              priority
              unoptimized
            />
          </div>
        )}

        {/* Two Column: Ingredients & Directions */}
        <div className="flex gap-6">
          {/* Ingredients Column */}
          <div className="w-1/3 p-3 border border-gray-200 rounded-lg bg-gray-50">
            <h2 className="pb-1 mb-2 text-base font-bold tracking-wide text-black uppercase border-b border-gray-300">
              Ingredients
            </h2>
            <div className="space-y-1 text-sm">
              {sortCategoryEntries(Array.from(groupedIngredients.entries())).map(([category, ingredients]) => (
                <div key={category}>
                  {groupedIngredients.size > 1 && (
                    <p className="mt-3 mb-1 text-xs font-semibold text-gray-700 uppercase first:mt-0">
                      {category}
                    </p>
                  )}
                  {ingredients.map((ingredient: RecipeResponseDTO["ingredients"][0]) => (
                    <p key={ingredient.id} className="text-black py-0.5">
                      <span className="font-medium">{formatQuantity(ingredient.quantity)} {ingredient.unit || ""}</span>
                      {(ingredient.quantity || ingredient.unit) && " "}
                      {ingredient.ingredient_name}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          </div>

          {/* Directions Column */}
          <div className="w-2/3 p-3 border border-gray-200 rounded-lg">
            <h2 className="pb-1 mb-2 text-base font-bold tracking-wide text-black uppercase border-b border-gray-300">
              Directions
            </h2>
            <ol className="ml-4 space-y-2 text-sm list-decimal list-outside">
              {directions.map((step, index) => (
                <li key={index} className="pl-1 leading-relaxed text-black">
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* Chef's Notes */}
        {printOptions.showNotes && recipe.notes && (
          <div className="p-3 mt-3 border border-gray-200 rounded-lg bg-gray-50">
            <h3 className="mb-1 text-sm font-bold text-black">Chef&apos;s Notes</h3>
            <p className="break-words text-xs text-gray-800 [overflow-wrap:anywhere]">{recipe.notes}</p>
          </div>
        )}

        {/* Nutrition Facts */}
        {printOptions.showNutrition && recipe.nutrition_facts && (
          <div className="p-3 mt-3 border border-gray-200 rounded-lg bg-gray-50">
            <h3 className="mb-2 text-sm font-bold text-black">
              Nutrition Facts{" "}
              <span className="font-normal text-gray-600">(per serving)</span>
            </h3>
            <div className="grid grid-cols-5 gap-2">
              {NUTRITION_PRINT_ROWS.map((row) => {
                const value = recipe.nutrition_facts![row.key];
                return (
                  <div
                    key={row.key}
                    className="px-2 py-1 text-center border border-gray-200 rounded bg-white"
                  >
                    <p className="text-sm font-bold text-black">
                      {formatNutritionValue(value)}
                      {value !== null && typeof value !== "boolean" && (
                        <span className="ml-0.5 text-xs font-medium text-gray-600">
                          {row.unit}
                        </span>
                      )}
                    </p>
                    <p className="text-xs text-gray-600">{row.label}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
