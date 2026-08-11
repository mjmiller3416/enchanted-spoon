"use client";

import {
  Clock,
  Timer,
  Flame,
  Users,
  Edit3,
  Trash2,
  Printer,
  CalendarPlus,
  UtensilsCrossed,
  Share2,
  FolderOpen,
  ChefHat,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { RecipeBadge, RecipeBadgeGroup } from "@/components/recipe/RecipeBadge";
import type { RecipeResponseDTO } from "@/types/recipe";
import { formatTime } from "../recipe-utils";
import { useRecipeGroupsForRecipe } from "@/hooks/api/useRecipeGroups";
import { useRecipeWizardDialog } from "@/lib/providers/RecipeWizardProvider";

interface RecipeHeaderCardProps {
  recipe: RecipeResponseDTO;
  recipeId: number;
  /** Whether Cook Mode (keep-screen-awake) is currently on. */
  cookMode: boolean;
  /** Whether the browser supports the wake lock — hides the toggle when false. */
  cookModeSupported: boolean;
  onCookModeToggle: () => void;
  onMealPlanClick: () => void;
  onManageGroupsClick: () => void;
  onPrintClick: () => void;
  onShare: () => void;
  onDelete: () => void;
}

/**
 * Header card component displaying recipe title, badges, stats, and action buttons.
 * Handles Edit, Print, Share, Delete, Add to Meal Plan, and Manage Groups actions.
 */
export function RecipeHeaderCard({
  recipe,
  recipeId,
  cookMode,
  cookModeSupported,
  onCookModeToggle,
  onMealPlanClick,
  onManageGroupsClick,
  onPrintClick,
  onShare,
  onDelete,
}: RecipeHeaderCardProps) {
  // Fetch recipe groups
  const { data: recipeGroups = [] } = useRecipeGroupsForRecipe(recipeId);
  const { openWizardForEdit } = useRecipeWizardDialog();

  return (
    <Card className="mb-8 shadow-xl">
      <CardContent className="p-6 md:p-8">
        {/* Recipe Name */}
        <h1 className="mb-2 text-3xl font-bold leading-tight md:text-4xl text-foreground">
          {recipe.recipe_name}
        </h1>

        {/* Description */}
        {recipe.description && (
          <p className="mb-4 text-muted-foreground leading-relaxed">
            {recipe.description}
          </p>
        )}

        {/* Badges */}
        <RecipeBadgeGroup className="mb-6">
          {recipe.meal_type && (
            <RecipeBadge
              label={recipe.meal_type}
              type="mealType"
              size="md"
            />
          )}
          {recipe.recipe_category && (
            <RecipeBadge
              label={recipe.recipe_category}
              type="category"
              size="md"
            />
          )}
          {recipe.diet_pref && (
            <RecipeBadge
              label={recipe.diet_pref}
              type="dietary"
              size="md"
            />
          )}
          {recipe.difficulty && (
            <RecipeBadge
              label={recipe.difficulty}
              type="difficulty"
              size="md"
            />
          )}
          {recipeGroups.length > 0 && (
            <RecipeBadge
              label={recipeGroups[0].name}
              type="group"
              size="md"
              groups={recipeGroups}
            />
          )}
          {recipe.is_ai_generated && (
            <RecipeBadge
              label="AI Generated"
              type="ai"
              size="md"
            />
          )}
          {recipe.source_url && (
            <Tooltip>
              <TooltipTrigger asChild>
                <a
                  href={recipe.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="View original recipe"
                >
                  <RecipeBadge
                    label="Imported"
                    type="imported"
                    size="md"
                  />
                </a>
              </TooltipTrigger>
              <TooltipContent>View original recipe</TooltipContent>
            </Tooltip>
          )}
        </RecipeBadgeGroup>

        {/* Quick Stats */}
        <div className="flex flex-wrap items-center gap-6 text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <Timer className="w-5 h-5 text-primary" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Prep Time</p>
              <p className="font-semibold text-foreground">
                {formatTime(recipe.prep_time)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <Flame className="w-5 h-5 text-primary" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Cook Time</p>
              <p className="font-semibold text-foreground">
                {formatTime(recipe.cook_time)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <Clock className="w-5 h-5 text-primary" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Time</p>
              <p className="font-semibold text-foreground">
                {formatTime(recipe.total_time)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <Users className="w-5 h-5 text-primary" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Servings</p>
              <p className="font-semibold text-foreground">
                {recipe.servings || "—"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10">
              <UtensilsCrossed className="w-5 h-5 text-primary" strokeWidth={1.5} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Ingredients</p>
              <p className="font-semibold text-foreground">
                {recipe.ingredients.length} items
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <Separator className="my-6 print:hidden" />

        <div className="flex flex-wrap gap-3 print:hidden">
          <Button
            onClick={onMealPlanClick}
            className="gap-2"
          >
            <CalendarPlus className="w-4 h-4" />
            Add to Meal Plan
          </Button>

          {cookModeSupported && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={cookMode ? "default" : "outline"}
                  className="gap-2"
                  onClick={onCookModeToggle}
                  aria-pressed={cookMode}
                >
                  <ChefHat className="w-4 h-4" />
                  {cookMode ? "Cook Mode On" : "Cook Mode"}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {cookMode
                  ? "Screen will stay awake — tap to turn off"
                  : "Keep the screen awake while you cook"}
              </TooltipContent>
            </Tooltip>
          )}

          <Button
            onClick={onManageGroupsClick}
            variant="secondary"
            className="gap-2"
          >
            <FolderOpen className="w-4 h-4" />
            Manage Groups
          </Button>

          <Button
            variant="outline"
            className="gap-2"
            onClick={() => openWizardForEdit(recipeId)}
          >
            <Edit3 className="w-4 h-4" />
            Edit Recipe
          </Button>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="icon" aria-label="Print recipe" onClick={onPrintClick}>
                <Printer className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Print Recipe</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="icon" aria-label="Share recipe" onClick={onShare}>
                <Share2 className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Share Recipe</TooltipContent>
          </Tooltip>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="icon" aria-label="Delete recipe" className="text-muted-foreground hover:text-error hover:border-error">
                <Trash2 className="w-4 h-4" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Recipe</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete &quot;{recipe.recipe_name}&quot;? This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={onDelete}
                  className="bg-error hover:bg-error/90"
                >
                  Delete Recipe
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
