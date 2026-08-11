"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Beaker, BookOpen, Lightbulb, UtensilsCrossed } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { FavoriteButton } from "@/components/common/FavoriteButton";
import { useWakeLock } from "@/hooks/ui";
import { backOrFallback } from "@/lib/navigation";
import type { RecipeResponseDTO, NutritionFactsResponseDTO } from "@/types/recipe";

import { sortCategoryEntries } from "./recipe-utils";
import { useRecipeView } from "./useRecipeView";
import { RecipeHeroImage, RecipeSkeleton, RecipeNotFound, RecipeHeaderCard } from "./detail";
import { IngredientItem, DirectionStep } from "./ingredients-directions";
import { AddToMealPlanDialog } from "./AddToMealPlanDialog";
import { ManageGroupsDialog } from "./ManageGroupsDialog";
import { PrintPreviewDialog, RecipePrintLayout, usePrintRecipe } from "./print";

// ============================================================================
// Nutrition Facts Card (local — only used in this view)
// ============================================================================

const NUTRITION_ROWS: {
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

function NutritionFactsCard({ nutritionFacts }: { nutritionFacts: NutritionFactsResponseDTO }) {
  const formatValue = (value: number | null | boolean): string => {
    if (value === null || typeof value === "boolean") return "—";
    return Number.isInteger(value) ? value.toString() : value.toFixed(1);
  };

  return (
    <Card className="mt-8 print:mt-4 print:static print:shadow-none print:border print:border-gray-200">
      <CardContent className="p-6 print:p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4 print:mb-2">
          <div className="flex items-center gap-3 print:gap-0">
            <div className="p-2 rounded-lg bg-primary/10 print:hidden">
              <Beaker className="size-5 text-primary" strokeWidth={1.5} />
            </div>
            <h2 className="text-xl font-bold text-foreground print:text-lg print:text-black">
              Nutrition Facts
            </h2>
            <span className="text-sm text-muted-foreground print:text-xs print:text-gray-500">
              Per serving
            </span>
          </div>
          {nutritionFacts.is_ai_estimated && (
            <Badge variant="secondary" className="print:hidden">AI Estimated</Badge>
          )}
        </div>
        <Separator className="mb-4" />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5 print:grid-cols-5">
          {NUTRITION_ROWS.map((row) => {
            const value = nutritionFacts[row.key];
            return (
              <div
                key={row.key}
                className="flex flex-col items-center justify-center rounded-lg bg-muted/50 p-3 text-center print:border print:border-gray-200 print:bg-white"
              >
                <span className="text-lg font-bold text-foreground print:text-base">
                  {formatValue(value)}
                  {value !== null && typeof value !== "boolean" && (
                    <span className="ml-0.5 text-sm font-medium text-muted-foreground">
                      {row.unit}
                    </span>
                  )}
                </span>
                <span className="mt-1 text-xs text-muted-foreground">{row.label}</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

// ============================================================================
// MAIN VIEW COMPONENT
// ============================================================================

export function FullRecipeView() {
  const params = useParams();
  const router = useRouter();
  const recipeId = Number(params.id);

  // Recipe data and handlers from custom hook
  const {
    recipe,
    loading,
    isFavorite,
    plannerEntries,
    directions,
    groupedIngredients,
    checkedIngredients,
    completedSteps,
    ingredientProgress,
    stepProgress,
    handleFavoriteToggle,
    handleIngredientToggle,
    handleStepToggle,
    handleDelete,
    handleMealAdded,
  } = useRecipeView(recipeId);

  // Print functionality from custom hook
  const { printDialogOpen, setPrintDialogOpen, printOptions, handlePrint } = usePrintRecipe();

  // Cook Mode — keep the screen awake while following the recipe
  const {
    isSupported: cookModeSupported,
    isActive: cookMode,
    toggle: toggleCookMode,
  } = useWakeLock();

  // Local state for dialogs
  const [mealPlanDialogOpen, setMealPlanDialogOpen] = useState(false);
  const [manageGroupsDialogOpen, setManageGroupsDialogOpen] = useState(false);

  // Share handler - copies URL to clipboard
  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success("Link copied to clipboard!");
  };

  // Loading state
  if (loading) {
    return <RecipeSkeleton />;
  }

  // Not found state
  if (!recipe) {
    return <RecipeNotFound />;
  }

  return (
    <>
      <div className="min-h-screen bg-background print:bg-white print:min-h-0">
        {/* Print-Only Layout */}
        <RecipePrintLayout
          recipe={recipe}
          directions={directions}
          groupedIngredients={groupedIngredients}
          printOptions={printOptions}
        />

        {/* Hero Image Section - Hidden for Print */}
        <div className="print:hidden">
          <RecipeHeroImage
            bannerSrc={recipe.banner_image_path}
            fallbackSrc={recipe.reference_image_path}
            alt={recipe.recipe_name}
          >
            {/* Back Button - Fixed Position */}
            <div className="absolute top-6 left-6">
              <Button
                variant="outline"
                size="sm"
                className="gap-2 bg-background/80 backdrop-blur-sm hover:bg-background"
                onClick={() => backOrFallback(router, "/recipes")}
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
            </div>

            {/* Favorite Button - Fixed Position */}
            <div className="absolute top-6 right-6">
              <FavoriteButton
                isFavorite={isFavorite}
                onToggle={handleFavoriteToggle}
                variant="overlay"
                size="lg"
              />
            </div>
          </RecipeHeroImage>
        </div>

        {/* Main Content - Hidden for Print */}
        <div className="relative z-10 max-w-5xl px-6 pb-12 mx-auto -mt-16 print:hidden">
          {/* Recipe Header Card */}
          <RecipeHeaderCard
            recipe={recipe}
            recipeId={recipeId}
            cookMode={cookMode}
            cookModeSupported={cookModeSupported}
            onCookModeToggle={toggleCookMode}
            onMealPlanClick={() => setMealPlanDialogOpen(true)}
            onManageGroupsClick={() => setManageGroupsDialogOpen(true)}
            onPrintClick={() => setPrintDialogOpen(true)}
            onShare={handleShare}
            onDelete={handleDelete}
          />

          {/* Two Column Layout: Ingredients & Directions */}
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 print:block print:space-y-6">
            {/* Ingredients Column */}
            <div className="lg:col-span-4 print:w-full">
              <Card className="print:shadow-none print:border print:border-gray-200">
                <CardContent className="p-6 print:p-4">
                  {/* Section Header */}
                  <div className="flex items-center justify-between mb-4 print:mb-2">
                    <div className="flex items-center gap-3 print:gap-0">
                      <div className="p-2 rounded-lg bg-secondary/10 print:hidden">
                        <BookOpen className="w-5 h-5 text-secondary" />
                      </div>
                      <h2 className="text-xl font-bold text-foreground print:text-lg print:text-black">
                        Ingredients
                      </h2>
                    </div>
                    {ingredientProgress > 0 && (
                      <span className="text-sm text-muted-foreground print:hidden">
                        {ingredientProgress}%
                      </span>
                    )}
                  </div>

                  {/* Progress Bar */}
                  {ingredientProgress > 0 && (
                    <div className="h-1.5 bg-elevated rounded-full overflow-hidden mb-4 print:hidden">
                      <div
                        className="h-full transition-all duration-300 bg-secondary"
                        style={{ width: `${ingredientProgress}%` }}
                      />
                    </div>
                  )}

                  {/* Ingredients List */}
                  {recipe.ingredients.length > 0 ? (
                    <div className="space-y-1">
                      {sortCategoryEntries(Array.from(groupedIngredients.entries())).map(([category, ingredients]) => (
                        <div key={category}>
                          {groupedIngredients.size > 1 && (
                            <p className="mt-4 mb-2 text-xs font-semibold tracking-wider uppercase text-muted-foreground first:mt-0">
                              {category}
                            </p>
                          )}
                          {ingredients.map((ingredient: RecipeResponseDTO["ingredients"][0]) => (
                            <IngredientItem
                              key={ingredient.id}
                              ingredient={ingredient}
                              checked={checkedIngredients.has(ingredient.id)}
                              onToggle={() => handleIngredientToggle(ingredient.id)}
                            />
                          ))}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="py-8 text-center text-muted-foreground">
                      No ingredients listed
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Directions Column */}
            <div className="lg:col-span-8 print:w-full">
              <Card className="print:shadow-none print:border print:border-gray-200">
                <CardContent className="p-6 print:p-4">
                  {/* Section Header */}
                  <div className="flex items-center justify-between mb-4 print:mb-2">
                    <div className="flex items-center gap-3 print:gap-0">
                      <div className="p-2 rounded-lg bg-primary/10 print:hidden">
                        <UtensilsCrossed className="w-5 h-5 text-primary" />
                      </div>
                      <h2 className="text-xl font-bold text-foreground print:text-lg print:text-black">
                        Directions
                      </h2>
                    </div>
                    {stepProgress > 0 && (
                      <span className="text-sm text-muted-foreground print:hidden">
                        {stepProgress}%
                      </span>
                    )}
                  </div>

                  {/* Progress Bar */}
                  {stepProgress > 0 && (
                    <div className="h-1.5 bg-elevated rounded-full overflow-hidden mb-4 print:hidden">
                      <div
                        className="h-full transition-all duration-300 bg-primary"
                        style={{ width: `${stepProgress}%` }}
                      />
                    </div>
                  )}

                  {/* Directions Steps */}
                  {directions.length > 0 ? (
                    <div className="space-y-2">
                      {directions.map((step, index) => (
                        <DirectionStep
                          key={index}
                          step={step}
                          index={index}
                          completed={completedSteps.has(index)}
                          onToggle={() => handleStepToggle(index)}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="py-8 text-center text-muted-foreground">
                      No directions available
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Notes Section */}
              {recipe.notes && (
                <Card className="mt-8 border-warning/30 bg-warning/5 print:mt-4 print:border print:border-gray-300 print:bg-gray-50 print:shadow-none">
                  <CardContent className="p-6 print:p-4">
                    <div className="flex items-start gap-4 print:gap-2">
                      <div className="flex-shrink-0 p-2 rounded-lg bg-warning/20 print:hidden">
                        <Lightbulb className="w-5 h-5 text-warning" />
                      </div>
                      <div>
                        <h3 className="mb-2 text-lg font-bold text-foreground print:text-base print:text-black print:mb-1">
                          Chef&apos;s Notes
                        </h3>
                        <p className="leading-relaxed text-foreground/80 print:text-sm print:text-black">
                          {recipe.notes}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Nutrition Facts - full-width horizontal strip */}
              {recipe.nutrition_facts && (
                <NutritionFactsCard nutritionFacts={recipe.nutrition_facts} />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add to Meal Plan Dialog */}
      <AddToMealPlanDialog
        recipe={recipe}
        plannerEntries={plannerEntries}
        open={mealPlanDialogOpen}
        onOpenChange={setMealPlanDialogOpen}
        onSuccess={handleMealAdded}
      />

      {/* Manage Groups Dialog */}
      <ManageGroupsDialog
        recipeId={recipeId}
        recipeName={recipe.recipe_name}
        open={manageGroupsDialogOpen}
        onOpenChange={setManageGroupsDialogOpen}
      />

      {/* Print Preview Dialog */}
      <PrintPreviewDialog
        open={printDialogOpen}
        onOpenChange={setPrintDialogOpen}
        onPrint={handlePrint}
        hasImage={!!recipe.reference_image_path}
        hasNotes={!!recipe.notes}
        hasNutrition={!!recipe.nutrition_facts}
      />
    </>
  );
}