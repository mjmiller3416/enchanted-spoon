"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { QueryError } from "@/components/common/QueryError";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/button";
import {
  usePlannerEntries,
  usePlannerSummary,
  useShoppingList,
  useRemoveEntry,
  useMarkComplete,
  useMarkIncomplete,
  useToggleSaveMeal,
  useSetShoppingMode,
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
import { MealDetailPane } from "./meal-display/MealDetailPane";
import { MealCreationOverlay } from "./MealCreationOverlay";
import { useSelectedMealParam } from "./useSelectedMealParam";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { useMediaQuery } from "@/hooks/ui/useMediaQuery";
import { ShoppingCart, Plus } from "lucide-react";

/**
 * Esc belongs to these while they're open: Radix dialogs/menus (including the
 * meal builder) and a card lifted for keyboard reordering (Esc cancels the drag).
 */
const ESC_OWNER_SELECTOR = [
  '[role="dialog"][data-state="open"]',
  '[role="alertdialog"][data-state="open"]',
  '[role="menu"][data-state="open"]',
  '[aria-roledescription="sortable"][aria-pressed="true"]',
].join(", ");

// ============================================================================
// MEAL PLANNER VIEW COMPONENT
// ============================================================================

/**
 * MealPlannerView - the Menu page (/meal-planner).
 *
 * The open meal is URL-driven (`?meal=<plannerEntryId>`, see
 * useSelectedMealParam); no param means nothing is open and no card is ringed.
 * On desktop (lg+) the page spans the full width and an open meal docks a
 * MealDetailPane to the right edge, pushing the grid over. On mobile the same
 * param drives a full-height bottom Sheet with SelectedMealCard.
 */
export function MealPlannerView() {
  const { getToken } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Fetch planner entries via React Query
  const { data: entries = [], isLoading, error: loadError, refetch, isFetching } = usePlannerEntries();

  // Planner summary supplies the server-owned capacity limit; the live count
  // comes from the entries cache so it tracks optimistic updates instantly
  const { data: plannerSummary } = usePlannerSummary();
  const maxCapacity = plannerSummary?.max_capacity;

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
  const setShoppingModeMutation = useSetShoppingMode();
  const reorderEntriesMutation = useReorderEntries();
  const clearCompletedMutation = useClearCompleted();

  // Selection lives in the URL (?meal=<entryId>); nothing is open without it
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const { selectedEntryId, openMeal, closeMeal } = useSelectedMealParam();
  // Element that opened the meal (usually a grid card) — refocused on close
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const [editLoading, setEditLoading] = useState(false);
  const setError = (message: string | null) => { if (message) toast.error(message); };
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
  // flow) navigate to /meal-planner?addMeal=1 — open the flow and drop only
  // that param, so an open `?meal=` survives
  useEffect(() => {
    if (searchParams.get("addMeal")) {
      openMealCreation();
      const params = new URLSearchParams(searchParams.toString());
      params.delete("addMeal");
      const query = params.toString();
      router.replace(query ? `/meal-planner?${query}` : "/meal-planner", { scroll: false });
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

  // Get the selected entry to derive meal_id for the pane / sheet
  const selectedEntry = entries.find((e) => e.id === selectedEntryId);
  const selectedMealId = selectedEntry?.meal_id ?? null;

  /**
   * Open (or swap to) an entry, remembering the focused element — the card or
   * dropdown item that opened it — so closing can hand focus back.
   */
  const openEntry = useCallback(
    (entryId: number) => {
      const active = document.activeElement;
      returnFocusRef.current =
        active instanceof HTMLElement && active !== document.body ? active : null;
      openMeal(entryId);
    },
    [openMeal]
  );

  /** Close the open meal and return focus to whatever opened it (if still mounted). */
  const closeEntry = useCallback(() => {
    closeMeal();
    const opener = returnFocusRef.current;
    returnFocusRef.current = null;
    if (opener?.isConnected) opener.focus({ preventScroll: true });
  }, [closeMeal]);

  /**
   * Next uncompleted entry after `entryId` in menu order (wrapping to the
   * start), never `entryId` itself; null when none remain.
   */
  const findNextUncompleted = (entryId: number): number | null => {
    const active = entries.filter((e) => !e.is_completed);
    const index = active.findIndex((e) => e.id === entryId);
    const ordered = index === -1 ? active : [...active.slice(index + 1), ...active.slice(0, index)];
    return ordered.find((e) => e.id !== entryId)?.id ?? null;
  };

  /** Show `entryId` when there is one, otherwise close the pane / sheet. */
  const showOrClose = (entryId: number | null) => {
    if (entryId === null) closeEntry();
    else openMeal(entryId);
  };

  // A stale or invalid ?meal= (removed, cleared, never existed) closes quietly.
  // Waits for settled data so a just-created entry isn't closed mid-refetch.
  useEffect(() => {
    if (selectedEntryId === null || isLoading || isFetching) return;
    if (!entries.some((e) => e.id === selectedEntryId)) closeEntry();
  }, [selectedEntryId, entries, isLoading, isFetching, closeEntry]);

  // Esc closes the desktop pane unless something layered above owns it
  useEffect(() => {
    if (!isDesktop || selectedEntryId === null) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented || overlayOpen) return;
      if (document.querySelector(ESC_OWNER_SELECTOR)) return;
      closeEntry();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDesktop, selectedEntryId, overlayOpen, closeEntry]);

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
    openEntry(item.id);
  };

  // Handle completed item selection
  const handleCompletedItemClick = (item: CompletedMealItem) => {
    openEntry(item.id);
  };

  // A meal was created (or a saved meal added) from the overlay — open it in
  // the desktop pane (on mobile the sheet stays closed, as before)
  const handleEntryCreated = useCallback(
    (entry: PlannerEntryResponseDTO) => {
      if (isDesktop) openMeal(entry.id);
    },
    [isDesktop, openMeal]
  );

  // A meal edit was saved — refresh the open meal's details
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
          // Refresh meal details to show updated recipe stats
          setMealRefreshKey((k) => k + 1);
        },
        onError: (err) => {
          setError(err instanceof Error ? err.message : "Failed to update completion status");
        },
      });
    } else {
      const completedId = selectedEntryId;

      // Advance to the next uncompleted meal right away (the hook updates the
      // grid optimistically); close when none are left
      showOrClose(findNextUncompleted(completedId));

      markCompleteMutation.mutate(completedId, {
        onSuccess: () => {
          // Refresh meal stats (times cooked, last cooked) for any reopen
          setMealRefreshKey((k) => k + 1);
        },
        onError: (err) => {
          // Bring the meal back into view on failure
          openMeal(completedId);
          setError(err instanceof Error ? err.message : "Failed to update completion status");
        },
      });
    }
  };

  // Handle Edit Meal button click - fetches meal data and opens the builder in edit mode
  const handleEditMeal = async () => {
    if (!selectedMealId) return;

    setEditLoading(true);
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
    } finally {
      setEditLoading(false);
    }
  };

  // Handle Add Side click - opens the builder in edit mode (starts on side picking)
  const handleAddSide = async () => {
    await handleEditMeal();
  };

  const handleRemoveFromMenu = () => {
    if (selectedEntryId === null) return;

    const entryToRemove = selectedEntryId;

    // Advance to the next uncompleted meal (or close) before removal —
    // optimistic UI handled by the hook
    showOrClose(findNextUncompleted(entryToRemove));

    removeEntryMutation.mutate(entryToRemove, {
      onError: (err) => {
        // Restore selection on error
        openMeal(entryToRemove);
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
  const handleSetShoppingMode = (item: MealGridItem, mode: NonNullable<MealGridItem["shoppingMode"]>) => {
    // Ignore repeated clicks on the same card while its toggle is still in flight —
    // firing overlapping requests races on the server's read of the current mode
    // and can lose an update (see issue #173).
    if (setShoppingModeMutation.isPending && setShoppingModeMutation.variables?.id === item.id) {
      return;
    }

    // Optimistic update handled by the hook
    setShoppingModeMutation.mutate({ id: item.id, mode }, {
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

    // Close the pane / sheet if the open meal is being cleared
    if (selectedEntryId !== null && completedIds.includes(selectedEntryId)) {
      closeEntry();
    }

    // Optimistic update handled by the hook
    clearCompletedMutation.mutate(undefined, {
      onError: (err) => {
        setError(err instanceof Error ? err.message : "Failed to clear completed");
      },
    });
  };

  if (loadError && !entries.length) return <PageLayout title="Menu"><QueryError title="Couldn’t load your menu" onRetry={() => void refetch()} retrying={isFetching} /></PageLayout>;

  const page = (
    <PageLayout
      fullWidth
      title="Menu"
      description="Choose your meals, arrange the order, and shop from your menu."
      actions={<>
        <Button onClick={openMealCreation} data-tour="planner-add-meal"><Plus className="size-4" strokeWidth={1.5} />Add meal</Button>
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
      </>}
    >
      {/* MENU SECTION: heading + grid */}
      <div className="space-y-4" data-tour="planner-menu">
        <div className="flex items-end gap-4">
          <h2 className="flex-1 text-lg font-semibold text-foreground">
            Planned meals
          </h2>
          {!isLoading && maxCapacity !== undefined && (
            <p
              className={cn(
                "text-sm whitespace-nowrap",
                activeEntries.length >= maxCapacity
                  ? "text-warning"
                  : "text-muted-foreground"
              )}
            >
              <span className="sm:hidden" aria-hidden="true">
                {activeEntries.length}/{maxCapacity}
              </span>
              <span className="sr-only sm:not-sr-only">
                {activeEntries.length} of {maxCapacity} meals planned
              </span>
            </p>
          )}
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
            onSetShoppingMode={handleSetShoppingMode}
            pendingShoppingModeId={
              setShoppingModeMutation.isPending
                ? (setShoppingModeMutation.variables?.id ?? null)
                : null
            }
            onReorder={handleReorder}
          />
        )}
      </div>

      {/* Mobile: the same ?meal= param drives a full-height bottom sheet */}
      {!isDesktop && (
        <Sheet
          open={selectedMealId !== null}
          onOpenChange={(open) => {
            if (!open) closeMeal();
          }}
        >
          <SheetContent side="bottom" className="h-dvh max-h-dvh overflow-y-auto">
            <SheetHeader>
              <SheetTitle>Meal details</SheetTitle>
              <SheetDescription>Review recipes and update this planned meal.</SheetDescription>
            </SheetHeader>
            <div className="p-4">
              {selectedMealId !== null && (
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
              )}
            </div>
          </SheetContent>
        </Sheet>
      )}

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

  // Desktop: the full-width page and the docked detail pane are siblings, so
  // the pane runs from under the TopNav beside the page header. The pane isn't
  // keyed — switching meals swaps its body without replaying the entrance.
  return (
    <div className="lg:flex lg:items-start">
      <div className="min-w-0 lg:flex-1">{page}</div>
      {isDesktop && selectedEntry && (
        <MealDetailPane
          mealId={selectedEntry.meal_id}
          mealName={selectedEntry.meal_name ?? "Untitled Meal"}
          isCompleted={selectedEntry.is_completed}
          isSaved={selectedEntry.meal_is_saved ?? false}
          refreshKey={mealRefreshKey}
          isCompletePending={
            (markCompleteMutation.isPending && markCompleteMutation.variables === selectedEntry.id) ||
            (markIncompleteMutation.isPending && markIncompleteMutation.variables === selectedEntry.id)
          }
          isSavePending={toggleSaveMutation.isPending && toggleSaveMutation.variables === selectedEntry.meal_id}
          isEditLoading={editLoading}
          onClose={closeEntry}
          onMarkComplete={handleMarkComplete}
          onEditMeal={handleEditMeal}
          onToggleSave={handleToggleSave}
          onRemove={handleRemoveFromMenu}
          onAddSide={handleAddSide}
        />
      )}
    </div>
  );
}
