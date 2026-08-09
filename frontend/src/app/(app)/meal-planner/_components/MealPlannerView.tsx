"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/button";
import {
  usePlannerEntries,
  useShoppingList,
  useRemoveEntry,
  useMarkComplete,
  useMarkIncomplete,
  useToggleSaveMeal,
  useCycleShoppingMode,
  useReorderEntries,
  useClearCompleted,
} from "@/hooks/api";
import { plannerApi } from "@/lib/api";
import type { PlannerEntryResponseDTO } from "@/types/planner";
import type { RecipeCardData } from "@/types/recipe";
import { MealGrid } from "./MealGrid";
import { MealGridItem } from "./MealGridCard";
import { MealGridSkeleton } from "./MealPlannerSkeleton";
import { CompletedDropdown, CompletedMealItem } from "./CompletedDropdown";
import { SelectedMealCard } from "./meal-display/SelectedMealCard";
import { MealCreationOverlay } from "./MealCreationOverlay";
import { ShoppingCart } from "lucide-react";

// ============================================================================
// MEAL PLANNER VIEW COMPONENT
// ============================================================================

export function MealPlannerView() {
  const { getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Fetch planner entries via React Query
  const { data: entries = [], isLoading } = usePlannerEntries();

  // Shopping list badge for the header action (same remaining-count logic as TopNav)
  const { data: shoppingData } = useShoppingList();
  const shoppingRemaining = shoppingData
    ? shoppingData.total_items - shoppingData.checked_items
    : 0;

  // Mutation hooks
  const removeEntryMutation = useRemoveEntry();
  const markCompleteMutation = useMarkComplete();
  const markIncompleteMutation = useMarkIncomplete();
  const toggleSaveMutation = useToggleSaveMeal();
  const cycleShoppingModeMutation = useCycleShoppingMode();
  const reorderEntriesMutation = useReorderEntries();
  const clearCompletedMutation = useClearCompleted();

  // Local UI state — selection falls back to the first uncompleted entry
  // until the user explicitly picks one (replaces the old auto-select effect)
  const [explicitSelectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const selectedEntryId =
    explicitSelectedEntryId ?? entries.find((e) => !e.is_completed)?.id ?? null;
  const [, setError] = useState<string | null>(null);
  const [mealRefreshKey, setMealRefreshKey] = useState(0);

  // Meal builder overlay state (the overlay owns the in-progress meal itself)
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [overlayMode, setOverlayMode] = useState<"create" | "edit">("create");
  const [editingMealId, setEditingMealId] = useState<number | null>(null);
  const [editingMealName, setEditingMealName] = useState<string | null>(null);
  const [initialMain, setInitialMain] = useState<RecipeCardData | null>(null);
  const [initialSides, setInitialSides] = useState<RecipeCardData[]>([]);

  // Open the meal builder in create mode (used by URL param handler and UI buttons)
  const openMealCreation = useCallback(() => {
    setOverlayMode("create");
    setEditingMealId(null);
    setEditingMealName(null);
    setInitialMain(null);
    setInitialSides([]);
    setOverlayOpen(true);
  }, [
    setOverlayMode,
    setEditingMealId,
    setEditingMealName,
    setInitialMain,
    setInitialSides,
    setOverlayOpen,
  ]);

  // Global "Add Meal" entry points (TopNav, mobile More sheet, Home first-run
  // flow) navigate to /meal-planner?addMeal=1 — open the flow and clean the URL
  useEffect(() => {
    if (searchParams.get("addMeal")) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing FROM the URL (external system) into dialog state
      openMealCreation();
      router.replace("/meal-planner", { scroll: false });
    }
  }, [searchParams, openMealCreation, router]);

  // Clear edit-mode prefill whenever the overlay closes
  const handleOverlayOpenChange = useCallback(
    (open: boolean) => {
      setOverlayOpen(open);
      if (!open) {
        setOverlayMode("create");
        setEditingMealId(null);
        setEditingMealName(null);
        setInitialMain(null);
        setInitialSides([]);
      }
    },
    [
      setOverlayOpen,
      setOverlayMode,
      setEditingMealId,
      setEditingMealName,
      setInitialMain,
      setInitialSides,
    ]
  );

  // Get the selected entry to derive meal_id for SelectedMealCard
  const selectedEntry = entries.find((e) => e.id === selectedEntryId);
  const selectedMealId = selectedEntry?.meal_id ?? null;

  // Split entries into active and completed
  const activeEntries = entries.filter((e) => !e.is_completed);
  const completedEntries = entries.filter((e) => e.is_completed);

  // Transform active entries to MealGridItem format
  const gridItems: MealGridItem[] = activeEntries.map((entry) => ({
    id: entry.id,
    name: entry.meal_name ?? "Untitled Meal",
    imageUrl: entry.main_recipe?.reference_image_path ?? null,
    bannerImageUrl: entry.main_recipe?.banner_image_path ?? null,
    servings: entry.main_recipe?.servings ?? null,
    totalTime: entry.main_recipe?.total_time ?? null,
    isSaved: entry.meal_is_saved ?? false,
    shoppingMode: entry.shopping_mode ?? "all",
  }));

  // Transform completed entries to CompletedMealItem format
  const completedItems: CompletedMealItem[] = completedEntries.map((entry) => ({
    id: entry.id,
    name: entry.meal_name ?? "Untitled Meal",
    imageUrl: entry.main_recipe?.reference_image_path ?? null,
    servings: entry.main_recipe?.servings ?? null,
    totalTime: entry.main_recipe?.total_time ?? null,
  }));

  // Handle grid item selection
  const handleGridItemClick = (item: MealGridItem) => {
    setSelectedEntryId(item.id);
  };

  // Handle completed item selection
  const handleCompletedItemClick = (item: CompletedMealItem) => {
    setSelectedEntryId(item.id);
  };

  // A meal was created (or a saved meal added) from the overlay — select it
  const handleEntryCreated = useCallback(
    (entry: PlannerEntryResponseDTO) => {
      setSelectedEntryId(entry.id);
    },
    [setSelectedEntryId]
  );

  // A meal edit was saved — refresh the selected meal card
  const handleMealUpdated = useCallback(() => {
    setMealRefreshKey((prev) => prev + 1);
  }, [setMealRefreshKey]);

  // Handle marking a meal as complete/incomplete (toggle)
  const handleMarkComplete = () => {
    if (selectedEntryId === null) return;

    const currentEntry = entries.find((e) => e.id === selectedEntryId);
    if (!currentEntry) return;

    // Use the appropriate mutation based on current state
    // Optimistic updates are handled by the hooks
    if (currentEntry.is_completed) {
      markIncompleteMutation.mutate(selectedEntryId, {
        onSuccess: () => {
          // Refresh meal card to show updated recipe stats
          setMealRefreshKey((k) => k + 1);
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : "Failed to update completion status");
        },
      });
    } else {
      markCompleteMutation.mutate(selectedEntryId, {
        onSuccess: () => {
          // Refresh meal card to show updated recipe stats (times cooked, last cooked)
          setMealRefreshKey((k) => k + 1);

          // Auto-select next uncompleted meal after marking complete
          // Filter out the current entry (now completed) to find remaining entries
          const remainingEntries = entries.filter((e) => e.id !== selectedEntryId);
          if (remainingEntries.length > 0) {
            // Try to find the first uncompleted entry
            const firstUncompleted = remainingEntries.find((e) => !e.is_completed);
            setSelectedEntryId(firstUncompleted?.id ?? null);
          } else {
            // No entries remain - clear selection to show empty state
            setSelectedEntryId(null);
          }
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : "Failed to update completion status");
        },
      });
    }
  };

  // Handle Edit Meal button click - fetches meal data and opens the builder in edit mode
  const handleEditMeal = async () => {
    if (!selectedMealId) return;

    try {
      const token = await getToken();
      const meal = await plannerApi.getMeal(selectedMealId, token);

      // Store the original meal name to preserve it during editing
      setEditingMealName(meal.meal_name);

      // Convert main recipe to RecipeCardData format
      setInitialMain(
        meal.main_recipe
          ? {
              id: meal.main_recipe.id,
              name: meal.main_recipe.recipe_name,
              servings: meal.main_recipe.servings ?? 0,
              totalTime: meal.main_recipe.total_time ?? 0,
              imageUrl: meal.main_recipe.reference_image_path ?? undefined,
            }
          : null
      );

      // Convert side recipes to RecipeCardData format
      setInitialSides(
        (meal.side_recipes ?? []).map((r) => ({
          id: r.id,
          name: r.recipe_name,
          servings: r.servings ?? 0,
          totalTime: r.total_time ?? 0,
          imageUrl: r.reference_image_path ?? undefined,
        }))
      );

      // Set edit mode and open the builder
      setEditingMealId(selectedMealId);
      setOverlayMode("edit");
      setOverlayOpen(true);
    } catch (err) {
      console.error("Failed to fetch meal for editing:", err);
      toast.error("Failed to load meal for editing");
    }
  };

  // Handle Add Side click - opens the builder in edit mode (starts on side picking)
  const handleAddSide = async () => {
    await handleEditMeal();
  };

  const handleRemoveFromMenu = () => {
    if (selectedEntryId === null) return;

    const entryToRemove = selectedEntryId;

    // Select next entry before removal (optimistic UI handled by hook)
    const remainingEntries = entries.filter((e) => e.id !== entryToRemove);
    if (remainingEntries.length > 0) {
      const firstUncompleted = remainingEntries.find((e) => !e.is_completed);
      setSelectedEntryId(firstUncompleted?.id ?? remainingEntries[0].id);
    } else {
      setSelectedEntryId(null);
    }

    removeEntryMutation.mutate(entryToRemove, {
      onError: (err) => {
        // Restore selection on error
        setSelectedEntryId(entryToRemove);
        setError(err instanceof Error ? err.message : "Failed to remove from menu");
      },
    });
  };

  // Handle toggling saved status for the selected meal
  const handleToggleSave = () => {
    if (!selectedMealId) return;

    // Optimistic update handled by the hook
    toggleSaveMutation.mutate(selectedMealId, {
      onError: (err) => {
        setError(err instanceof Error ? err.message : "Failed to update saved status");
      },
    });
  };

  // Handle cycling shopping mode for a meal: all -> produce_only -> none -> all
  const handleCycleShoppingMode = (item: MealGridItem) => {
    // Ignore repeated clicks on the same card while its toggle is still in flight —
    // firing overlapping requests races on the server's read of the current mode
    // and can lose an update (see issue #173).
    if (cycleShoppingModeMutation.isPending && cycleShoppingModeMutation.variables === item.id) {
      return;
    }

    // Optimistic update handled by the hook
    cycleShoppingModeMutation.mutate(item.id, {
      onError: (err) => {
        setError(err instanceof Error ? err.message : "Failed to update shopping mode");
      },
    });
  };

  // Handle drag-and-drop reorder of grid items
  const handleReorder = useCallback(
    (reorderedItems: MealGridItem[]) => {
      const reorderedIds = reorderedItems.map((item) => item.id);
      // Optimistic update handled by the hook
      reorderEntriesMutation.mutate(reorderedIds);
    },
    [reorderEntriesMutation]
  );

  // Handle clearing all completed entries
  const handleClearCompleted = () => {
    const completedIds = entries.filter((e) => e.is_completed).map((e) => e.id);
    const remainingEntries = entries.filter((e) => !e.is_completed);

    // Update selection if current selection was completed
    if (selectedEntryId && completedIds.includes(selectedEntryId)) {
      if (remainingEntries.length > 0) {
        setSelectedEntryId(remainingEntries[0].id);
      } else {
        setSelectedEntryId(null);
      }
    }

    // Optimistic update handled by the hook
    clearCompletedMutation.mutate(undefined, {
      onError: (err) => {
        setError(err instanceof Error ? err.message : "Failed to clear completed");
      },
    });
  };

  return (
    <PageLayout
      title="Meal Planner"
      description="Build your week in minutes. Balanced, realistic, repeatable."
      actions={
        <Button variant="outline" asChild>
          <Link href="/shopping-list">
            <ShoppingCart className="size-4" strokeWidth={1.5} />
            Shopping list
            {shoppingRemaining > 0 && (
              <span className="min-w-5 h-5 px-1.5 flex items-center justify-center rounded-full text-xs font-semibold bg-error/20 border border-error/30 text-error">
                {shoppingRemaining > 99 ? "99+" : shoppingRemaining}
              </span>
            )}
          </Link>
        </Button>
      }
    >
      {/* STACKED VERTICAL LAYOUT */}
      <div className="space-y-8">
        {/* TOP: MENU SECTION (heading + grid grouped with space-y-4, matching SelectedMealCard) */}
        <div className="space-y-4">
          <div className="flex items-end gap-4">
            <h2 className="flex-1 text-lg font-semibold text-foreground">
              This Week&apos;s Menu
            </h2>
            <CompletedDropdown
              items={completedItems}
              onItemClick={handleCompletedItemClick}
              onClearCompleted={handleClearCompleted}
            />
          </div>
          {isLoading ? (
            <MealGridSkeleton />
          ) : (
            <MealGrid
              items={gridItems}
              selectedId={selectedEntryId}
              onItemClick={handleGridItemClick}
              onAddMealClick={openMealCreation}
              onCycleShoppingMode={handleCycleShoppingMode}
              pendingShoppingModeId={
                cycleShoppingModeMutation.isPending
                  ? (cycleShoppingModeMutation.variables ?? null)
                  : null
              }
              onReorder={handleReorder}
            />
          )}
        </div>

        {/* BOTTOM: SELECTED MEAL CARD */}
        {selectedMealId !== null ? (
          <SelectedMealCard
            key={`meal-${selectedMealId}-${mealRefreshKey}`}
            mealId={selectedMealId}
            isCompleted={selectedEntry?.is_completed}
            isSaved={selectedEntry?.meal_is_saved}
            onMarkComplete={handleMarkComplete}
            onEditMeal={handleEditMeal}
            onToggleSave={handleToggleSave}
            onRemove={handleRemoveFromMenu}
            onAddSide={handleAddSide}
          />
        ) : (
          !isLoading && (
            /* Empty state when no meals in planner */
            <div className="flex flex-col items-center justify-center text-center min-h-96 px-8">
              <div className="text-muted-foreground mb-6">
                <p className="text-lg font-medium mb-2">No meals planned yet</p>
                <p className="text-sm">
                  Add a meal to your weekly menu to get started
                </p>
              </div>
              <Button onClick={openMealCreation} size="default">
                + Add Meal
              </Button>
            </div>
          )
        )}
      </div>

      {/* Meal builder — two-panel overlay for creating and editing meals */}
      <MealCreationOverlay
        open={overlayOpen}
        onOpenChange={handleOverlayOpenChange}
        mode={overlayMode}
        editingMealId={editingMealId}
        editingMealName={editingMealName}
        initialMain={initialMain}
        initialSides={initialSides}
        onEntryCreated={handleEntryCreated}
        onMealUpdated={handleMealUpdated}
      />
    </PageLayout>
  );
}
