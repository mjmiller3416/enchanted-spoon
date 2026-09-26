"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { CalendarPlus, Check, Plus, ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { RecipeResponseDTO } from "@/types/recipe";
import type { PlannerEntryResponseDTO } from "@/types/planner";
import { cn, getErrorMessage } from "@/lib/utils";
import {
  useAddSideToMeal,
  useCreateMeal,
  useAddToPlanner,
  useDiscardMeal,
} from "@/hooks/api";

interface AddToMealPlanDialogProps {
  recipe: RecipeResponseDTO;
  plannerEntries: PlannerEntryResponseDTO[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function AddToMealPlanDialog({
  recipe,
  plannerEntries,
  open,
  onOpenChange,
  onSuccess,
}: AddToMealPlanDialogProps) {
  const router = useRouter();

  // Mutation hooks
  const addSideToMealMutation = useAddSideToMeal();
  const createMealMutation = useCreateMeal();
  const addToPlannerMutation = useAddToPlanner();
  const discardMeal = useDiscardMeal();

  // Track the planner entry ID (unique), not meal_id (can have duplicates)
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [added, setAdded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<"select" | "create">("select");
  const [newMealName, setNewMealName] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Filter to only show meals with room for more sides (< 3)
  const availableMeals = plannerEntries.filter(
    (entry) => entry.side_recipe_ids.length < 3
  );

  const resetState = () => {
    setAdded(false);
    setSelectedEntryId(null);
    setMode("select");
    setNewMealName("");
    setError(null);
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      resetState();
    }
    onOpenChange(isOpen);
  };

  const showSuccess = () => {
    setAdded(true);
    onSuccess?.();
    toast.success(
      mode === "create" ? "Meal added to your planner" : "Added as a side dish",
      {
        action: {
          label: "View planner",
          onClick: () => router.push("/meal-planner"),
        },
      }
    );
    setTimeout(() => {
      handleOpenChange(false);
    }, 1500);
  };

  const handleAdd = async () => {
    if (!selectedEntryId) return;

    // Find the entry to get the meal_id
    const selectedEntry = availableMeals.find((e) => e.id === selectedEntryId);
    if (!selectedEntry) return;

    setIsLoading(true);
    setError(null);

    try {
      await addSideToMealMutation.mutateAsync({
        mealId: selectedEntry.meal_id,
        recipeId: recipe.id,
      });
      showSuccess();
    } catch (err) {
      console.error("Failed to add to meal:", err);
      setError("Failed to add recipe to meal. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateNew = async () => {
    if (!newMealName.trim()) return;

    setIsLoading(true);
    setError(null);

    let createdMealId: number | null = null;
    try {
      // Create a new meal with this recipe as the main dish
      const meal = await createMealMutation.mutateAsync({
        meal_name: newMealName.trim(),
        main_recipe_id: recipe.id,
        side_recipe_ids: [],
        tags: [],
      });
      createdMealId = meal.id;

      // Add the new meal to the planner
      await addToPlannerMutation.mutateAsync(meal.id);
      createdMealId = null;
      showSuccess();
    } catch (err) {
      console.error("Failed to create meal:", err);
      // Don't leave an unplanned copy behind for every retry
      if (createdMealId !== null) void discardMeal(createdMealId);
      setError(getErrorMessage(err, "Failed to create meal. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md bg-card">
        <DialogHeader>
          <DialogTitle>Add to Meal Plan</DialogTitle>
          <DialogDescription>
            {mode === "select"
              ? `Choose a meal to add "${recipe.recipe_name}" to, or create a new meal.`
              : `Create a new meal with "${recipe.recipe_name}" as the main dish.`}
          </DialogDescription>
        </DialogHeader>

        {added ? (
          <div className="py-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-success/20 flex items-center justify-center">
              <Check className="h-8 w-8 text-success" />
            </div>
            <p className="text-foreground font-medium">
              {mode === "create" ? "Meal Created!" : "Added to Meal!"}
            </p>
          </div>
        ) : mode === "create" ? (
          <>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <label htmlFor="meal-name" className="text-sm font-medium">
                  Meal Name
                </label>
                <Input
                  id="meal-name"
                  placeholder="e.g., Tuesday Dinner"
                  value={newMealName}
                  onChange={(e) => setNewMealName(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}
            </div>

            <DialogFooter className="gap-3">
              <Button
                variant="outline"
                onClick={() => setMode("select")}
                disabled={isLoading}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button
                onClick={handleCreateNew}
                disabled={!newMealName.trim() || isLoading}
                className="gap-2"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                Create Meal
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="space-y-2 max-h-[300px] overflow-y-auto py-2 px-6 -mx-6">
              {/* Create new meal button */}
              <button
                onClick={() => {
                  setMode("create");
                  setNewMealName(recipe.recipe_name);
                }}
                className="w-full p-4 rounded-lg border border-dashed border-primary/50 bg-elevated text-left transition-colors hover:bg-hover hover:border-primary"
              >
                <div className="flex items-center gap-2">
                  <Plus className="h-4 w-4 text-primary" />
                  <p className="font-medium text-primary">Create new meal</p>
                </div>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Add &quot;{recipe.recipe_name}&quot; as the main dish
                </p>
              </button>

              {/* Available meals from planner */}
              {availableMeals.length > 0 ? (
                availableMeals.map((entry) => (
                  <button
                    key={entry.id}
                    onClick={() => setSelectedEntryId(entry.id)}
                    className={cn(
                      "w-full p-4 rounded-lg border text-left transition-colors",
                      selectedEntryId === entry.id
                        ? "border-primary bg-primary/10"
                        : "bg-elevated border-border hover:bg-hover hover:border-primary/50"
                    )}
                  >
                    <p className="font-medium text-foreground">
                      {entry.meal_name || "Unnamed Meal"}
                    </p>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      {entry.main_recipe
                        ? `Main: ${entry.main_recipe.recipe_name}`
                        : "No main dish"}
                      {entry.side_recipe_ids.length > 0 &&
                        ` · ${entry.side_recipe_ids.length}/3 sides`}
                    </p>
                  </button>
                ))
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No meals in your planner have room for more sides.
                </p>
              )}
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <DialogFooter className="gap-3">
              <Button
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAdd}
                disabled={!selectedEntryId || isLoading}
                className="gap-2"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CalendarPlus className="h-4 w-4" />
                )}
                Add as Side
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
