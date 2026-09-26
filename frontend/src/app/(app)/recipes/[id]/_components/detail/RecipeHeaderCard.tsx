"use client";
import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { recipeApi } from "@/lib/api";

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
  Loader2,
  MoreHorizontal,
} from "lucide-react";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
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
  cookModeHeld: boolean;
  /** Whether the browser supports the wake lock — hides the toggle when false. */
  cookModeSupported: boolean;
  onCookModeToggle: () => void;
  onMealPlanClick: () => void;
  onManageGroupsClick: () => void;
  onPrintClick: () => void;
  onShare: () => void;
  onDelete: () => Promise<void>;
}

/**
 * Header card component displaying recipe title, badges, stats, and action buttons.
 * Handles Edit, Print, Share, Delete, Add to Meal Plan, and Manage Groups actions.
 */
export function RecipeHeaderCard({
  recipe,
  recipeId,
  cookMode,
  cookModeHeld,
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
  const { getToken } = useAuth();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const impact = useQuery({ queryKey: ["recipes", "deletion-impact", recipeId], enabled: deleteOpen,
    queryFn: async () => recipeApi.deletionImpact(recipeId, await getToken()) });

  return (
    <Card className="mb-6 shadow-sm">
      <CardContent className="p-4 sm:p-6">
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
          {recipe.is_sample && (
            <RecipeBadge
              label="Sample"
              type="sample"
              size="md"
            />
          )}
        </RecipeBadgeGroup>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 text-muted-foreground">
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
            <CalendarPlus className="w-4 h-4" strokeWidth={1.5} />
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
                  <ChefHat className="w-4 h-4" strokeWidth={1.5} />
                  {cookMode ? (cookModeHeld ? "Screen awake" : "Screen lock paused") : "Cook Mode"}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {cookMode
                  ? (cookModeHeld ? "Screen wake lock is active — tap to turn off" : "The browser has not acquired a screen wake lock — tap to turn off")
                  : "Keep the screen awake while you cook"}
              </TooltipContent>
            </Tooltip>
          )}

          <Button
            variant="outline"
            className="gap-2"
            onClick={() => openWizardForEdit(recipeId)}
          >
            <Edit3 className="w-4 h-4" strokeWidth={1.5} />
            Edit Recipe
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button variant="outline" aria-label="More recipe actions"><MoreHorizontal className="size-4" strokeWidth={1.5} />More</Button></DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={onManageGroupsClick}><FolderOpen className="size-4" strokeWidth={1.5} />Manage groups</DropdownMenuItem>
              <DropdownMenuItem onSelect={onPrintClick}><Printer className="size-4" strokeWidth={1.5} />Print recipe</DropdownMenuItem>
              <DropdownMenuItem onSelect={onShare}><Share2 className="size-4" strokeWidth={1.5} />Copy private link</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onSelect={() => setDeleteOpen(true)}><Trash2 className="size-4" strokeWidth={1.5} />Delete recipe</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <AlertDialog open={deleteOpen} onOpenChange={value => { if (!deleting) setDeleteOpen(value); }}>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Recipe</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete &quot;{recipe.recipe_name}&quot;? This action cannot be undone.
                  {impact.isLoading && <span className="mt-2 block">Checking affected meals…</span>}
                  {impact.data && impact.data.total_affected > 0 && <span className="mt-2 block">This also deletes {impact.data.meals_to_delete.length} meal(s) and removes this recipe from the sides of {impact.data.meals_to_update.length} meal(s).</span>}
                  {impact.isError && <span className="mt-2 block text-destructive">Couldn&apos;t check affected meals. <Button variant="link" size="sm" onClick={() => void impact.refetch()}>Retry</Button></span>}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  disabled={deleting || !impact.data || impact.isFetching || impact.isError}
                  onClick={async event => { event.preventDefault(); setDeleting(true); try { await onDelete(); setDeleteOpen(false); } catch { /* The mutation shows the error; keep confirmation open. */ } finally { setDeleting(false); } }}
                  className="bg-error hover:bg-error/90"
                >
                  {deleting && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}Delete Recipe
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
