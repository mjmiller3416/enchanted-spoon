"use client";
import { toast } from "sonner";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/button";
import { ShoppingCategory } from "./ShoppingCategory";
import { ShoppingListSkeleton } from "./ShoppingListSkeleton";
import {
  usePlannerEntries,
  useMeals,
  useShoppingList,
  useToggleItem,
  useToggleFlagged,
  useClearManualItems,
} from "@/hooks/api";
import type { ShoppingItemResponseDTO } from "@/types/shopping";
import { ShoppingCart, CalendarDays, Eye, EyeOff, Filter, X, Trash2, Clock, CheckCircle, Package } from "lucide-react";
import { StatCard } from "@/components/common/StatCard";
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
import { QuickAddForm } from "@/components/forms/QuickAddForm";
import { getErrorMessage } from "@/lib/utils";
import { IngredientSourceSidebar } from "./IngredientSourceSidebar";
import { useSettings } from "@/hooks/persistence/useSettings";

/**
 * ShoppingListView - Main shopping list page component
 *
 * Features:
 * - Auto-generates shopping list from active planner entries on mount (via auto_generate param)
 * - Groups items by category
 * - Optimistic UI updates for toggling items (via React Query mutations)
 * - Clear completed action
 * - Empty state when no items
 * - Loading skeleton during fetch
 */
export function ShoppingListView() {
  // Settings for category ordering and hide-completed
  const { settings, updateSettings, isLoaded: settingsLoaded } = useSettings();
  const { categorySortOrder, customCategoryOrder, hideCompleted } = settings.shoppingList;

  // React Query hooks for data fetching and mutations
  const { data: shoppingData, isLoading, error, refetch } = useShoppingList();
  const toggleItem = useToggleItem();
  const toggleFlagged = useToggleFlagged();
  const clearManualItems = useClearManualItems();
  // Fetch planner entries and meals for recipe ordering (using authenticated hooks)
  const { data: plannerEntries } = usePlannerEntries();
  const { data: allMeals } = useMeals();

  // UI state
  const [filterRecipeName, setFilterRecipeName] = useState<string | null>(null);

  // One-time migration of the old raw-localStorage hide-completed flag into
  // the settings store (runs after load so the API snapshot can't clobber it)
  useEffect(() => {
    if (!settingsLoaded) return;
    const legacy = localStorage.getItem("shopping-list-hide-completed");
    if (legacy === null) return;
    localStorage.removeItem("shopping-list-hide-completed");
    if (legacy === "true") {
      updateSettings("shoppingList", { hideCompleted: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- migration runs once, when settings finish loading
  }, [settingsLoaded]);

  // Clear manual items dialog state
  const [showClearManualDialog, setShowClearManualDialog] = useState(false);


  // Handle toggling an item's checked state
  const handleToggleItem = (itemId: number) => {
    toggleItem.mutate(itemId, { onError: () => toast.error("Couldn't update this item. Please try again.") });
  };

  // Handle toggling an item's flagged state
  const handleToggleFlagged = (itemId: number) => {
    toggleFlagged.mutate(itemId, { onError: () => toast.error("Couldn't update the flag. Please try again.") });
  };

  // Toggle hiding completed items (persists via the settings store)
  const handleToggleHideCompleted = () => {
    updateSettings("shoppingList", { hideCompleted: !hideCompleted });
  };

  // Handle clearing all manual items
  const handleClearManualItems = () => {
    // Compute unchecked manual items directly from data
    const manualItems = shoppingData?.items.filter((i) => i.source === "manual") ?? [];
    const uncheckedManualItems = manualItems.filter((i) => !i.have);

    if (uncheckedManualItems.length > 0) {
      // Show confirmation dialog if there are unchecked manual items
      setShowClearManualDialog(true);
    } else {
      // No unchecked items, proceed directly
      confirmClearManualItems();
    }
  };

  // Confirm and execute clearing manual items
  const confirmClearManualItems = () => {
    setShowClearManualDialog(false);
    clearManualItems.mutate();
  };

  // Filter items based on hideCompleted setting, then group by category
  const itemsToShow = hideCompleted
    ? shoppingData?.items.filter((item) => !item.have) ?? []
    : shoppingData?.items ?? [];

  const groupedItems = itemsToShow.reduce<Record<string, ShoppingItemResponseDTO[]>>(
    (acc, item) => {
      // Normalize to lowercase so pre-existing rows stored with mismatched casing
      // (e.g. "Other" vs "other") group together instead of splitting into two sections.
      const category = (item.category || "other").trim().toLowerCase();
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(item);
      return acc;
    },
    {}
  );

  // Compute unique recipes from all items for the sidebar
  const recipeData = shoppingData?.items.reduce<
    Record<string, { itemCount: number; collectedCount: number }>
  >((acc, item) => {
    if (item.source === "recipe" && item.recipe_sources) {
      for (const source of item.recipe_sources) {
        if (!acc[source.recipe_name]) {
          acc[source.recipe_name] = { itemCount: 0, collectedCount: 0 };
        }
        acc[source.recipe_name].itemCount++;
        if (item.have) {
          acc[source.recipe_name].collectedCount++;
        }
      }
    }
    return acc;
  }, {}) ?? {};

  // Build ordered recipe entries preserving duplicates across meals
  const { orderedRecipeEntries, duplicateRecipeNames } = useMemo(() => {
    const entries: Array<{
      recipeName: string;
      mealId: number;
      isFirstInMeal: boolean;
      instanceKey: string;
    }> = [];
    const recipeNameCounts = new Map<string, number>();

    if (!plannerEntries || !allMeals) return { orderedRecipeEntries: entries, duplicateRecipeNames: new Set<string>() };

    // Sort entries by position (meal planner order)
    // Include entries in "all" or "produce_only" mode (not "none")
    const sortedEntries = [...plannerEntries]
      .filter((e) => e.shopping_mode !== "none" && !e.is_completed)
      .sort((a, b) => a.position - b.position);

    for (const entry of sortedEntries) {
      // Find the full meal data to get side recipes
      const meal = allMeals.find((m) => m.id === entry.meal_id);
      if (!meal) continue;

      // Use planner entry ID for uniqueness (same meal can appear in multiple entries)
      const entryId = entry.id;

      // Add main recipe first (mark as first in meal)
      if (meal.main_recipe?.recipe_name) {
        const name = meal.main_recipe.recipe_name;
        entries.push({
          recipeName: name,
          mealId: meal.id,
          isFirstInMeal: true,
          instanceKey: `entry-${entryId}-main-${name}`,
        });
        recipeNameCounts.set(name, (recipeNameCounts.get(name) ?? 0) + 1);
      }

      // Add sides in order (always — no dedup guard)
      for (let i = 0; i < (meal.side_recipes || []).length; i++) {
        const side = meal.side_recipes![i];
        if (side.recipe_name) {
          const name = side.recipe_name;
          entries.push({
            recipeName: name,
            mealId: meal.id,
            isFirstInMeal: false,
            instanceKey: `entry-${entryId}-side-${i}-${name}`,
          });
          recipeNameCounts.set(name, (recipeNameCounts.get(name) ?? 0) + 1);
        }
      }
    }

    // Any recipe appearing in 2+ meals is a duplicate
    const duplicates = new Set<string>();
    for (const [name, count] of recipeNameCounts) {
      if (count > 1) duplicates.add(name);
    }

    return { orderedRecipeEntries: entries, duplicateRecipeNames: duplicates };
  }, [plannerEntries, allMeals]);

  // Build recipes array from ordered entries (already in planner position order)
  const recipes = orderedRecipeEntries
    .filter((entry) => recipeData[entry.recipeName])
    .map((entry) => ({
      name: entry.recipeName,
      itemCount: recipeData[entry.recipeName]?.itemCount ?? 0,
      collectedCount: recipeData[entry.recipeName]?.collectedCount ?? 0,
      isFirstInMeal: entry.isFirstInMeal,
      isDuplicate: duplicateRecipeNames.has(entry.recipeName),
      instanceKey: entry.instanceKey,
    }));

  // Count manual items
  const manualItems = shoppingData?.items.filter((i) => i.source === "manual") ?? [];
  const manualItemCount = manualItems.length;
  const manualCollectedCount = manualItems.filter((i) => i.have).length;

  // Filter items based on selected recipe
  const getFilteredItems = (items: ShoppingItemResponseDTO[]) => {
    if (!filterRecipeName) return items;
    if (filterRecipeName === "__manual__") {
      return items.filter((i) => i.source === "manual");
    }
    return items.filter((i) =>
      i.recipe_sources?.some((source) => source.recipe_name === filterRecipeName)
    );
  };

  // Normalize category name for comparison (handles slug vs display name mismatches)
  // e.g., "oils-and-vinegars" -> "Oils And Vinegars"
  const normalizeCategoryForComparison = (category: string): string => {
    return category
      .replace(/-/g, " ")
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ");
  };

  // Find category index in custom order (handles both exact match and normalized match)
  const findCategoryIndex = (category: string, customOrder: string[]): number => {
    // Try exact match first
    const exactIndex = customOrder.indexOf(category);
    if (exactIndex !== -1) return exactIndex;

    // Try normalized comparison
    const normalizedCategory = normalizeCategoryForComparison(category).toLowerCase();
    return customOrder.findIndex(
      (c) => normalizeCategoryForComparison(c).toLowerCase() === normalizedCategory
    );
  };

  // Sort categories based on user preference
  const sortedCategories = Object.keys(groupedItems).sort((a, b) => {
    // "other" always goes to the end
    if (a === "other") return 1;
    if (b === "other") return -1;

    if (categorySortOrder === "custom" && customCategoryOrder.length > 0) {
      // Use custom order with normalized matching
      const indexA = findCategoryIndex(a, customCategoryOrder);
      const indexB = findCategoryIndex(b, customCategoryOrder);
      // If both are in the custom order, sort by position
      if (indexA !== -1 && indexB !== -1) return indexA - indexB;
      // If only one is in custom order, it comes first
      if (indexA !== -1) return -1;
      if (indexB !== -1) return 1;
      // Neither in custom order - fallback to alphabetical
      return a.localeCompare(b);
    }

    // Default: alphabetical sorting
    return a.localeCompare(b);
  });

  // Filter out categories with no matching items when filter is active
  const visibleCategories = filterRecipeName
    ? sortedCategories.filter((cat) => getFilteredItems(groupedItems[cat]).length > 0)
    : sortedCategories;

  const hasItems = shoppingData && shoppingData.items.length > 0;
  const hasCheckedItems = shoppingData && shoppingData.checked_items > 0;

  // Header actions
  const headerActions = (
    <>
      {/* Clear manual items button - show only when there are manual items */}
      {manualItemCount > 0 && (
        <Button
          variant="outline"
          onClick={handleClearManualItems}
        >
          <Trash2 className="w-4 h-4 mr-2" />
          Clear manual
        </Button>
      )}
      {/* Show toggle button when there are checked items */}
      {hasCheckedItems && (
        <Button
          variant="outline"
          onClick={handleToggleHideCompleted}
        >
          {hideCompleted ? (
            <>
              <Eye className="w-4 h-4 mr-2" />
              Show collected
            </>
          ) : (
            <>
              <EyeOff className="w-4 h-4 mr-2" />
              Hide collected
            </>
          )}
        </Button>
      )}
    </>
  );

  // Loading skeleton (matches final layout; same component as the route loading boundary)
  if (isLoading) {
    return <ShoppingListSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <PageLayout
        title="Shopping List"
        description="Everything you need, consolidated and ready for the store."
        actions={headerActions}
      >
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="p-4 mb-4 rounded-full bg-destructive/10">
            <ShoppingCart className="w-12 h-12 text-destructive" />
          </div>
          <h2 className="mb-2 text-lg font-semibold text-foreground">
            Something went wrong
          </h2>
          <p className="max-w-sm mb-4 text-sm text-muted-foreground">
            {getErrorMessage(error, "Failed to load shopping list")}
          </p>
          <Button onClick={() => refetch()}>Try Again</Button>
        </div>
      </PageLayout>
    );
  }

  // Empty state
  if (!hasItems) {
    return (
      <PageLayout
        title="Shopping List"
        description="Everything you need, consolidated and ready for the store."
        actions={headerActions}
      >
        {/* Add manual item form - also available when list is empty */}
        <QuickAddForm variant="inline" />

        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="p-4 mb-4 rounded-full bg-elevated">
            <ShoppingCart className="w-12 h-12 text-muted-foreground" />
          </div>
          <h2 className="mb-2 text-lg font-semibold text-foreground">
            Your shopping list is empty
          </h2>
          <p className="max-w-sm mb-4 text-sm text-muted-foreground">
            Add meals to your planner or use the form above to add items manually.
          </p>
          <Button asChild>
            <Link href="/meal-planner">
              <CalendarDays className="size-4" strokeWidth={1.5} />
              Open meal planner
            </Link>
          </Button>
        </div>
      </PageLayout>
    );
  }

  // Calculate remaining items and progress
  const remainingItems = shoppingData.total_items - shoppingData.checked_items;
  const progressPercent =
    shoppingData.total_items > 0
      ? Math.round((shoppingData.checked_items / shoppingData.total_items) * 100)
      : 0;

  // Get Username for active filter
  const getFilteruserName = () => {
    if (!filterRecipeName) return null;
    if (filterRecipeName === "__manual__") return "Manual items";
    return filterRecipeName;
  };

  return (
    <PageLayout
      title="Shopping List"
      description="Everything you need, consolidated and ready for the store."
      actions={headerActions}
      pinActionsToNav
    >
      {/* Summary stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <StatCard
          icon={Clock}
          value={remainingItems}
          label="Remaining"
          colorClass="green"
        />
        <StatCard
          icon={CheckCircle}
          value={shoppingData.checked_items}
          label="Collected"
          colorClass="amber"
        />
        <StatCard
          icon={Package}
          value={shoppingData.total_items}
          label="Total Items"
          colorClass="purple"
        />
      </div>

      {/* Overall progress bar */}
      <div className="flex items-center gap-3 mb-6">
        <div className="flex-1 h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full transition-all duration-500 ease-out rounded-full bg-success"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="text-sm text-right text-muted-foreground tabular-nums min-w-10">
          {progressPercent}%
        </span>
      </div>

      {/* Add manual item form */}
      <QuickAddForm variant="inline" />

      {/* Two-column layout: Main content + Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_clamp(200px,25%,320px)] gap-6">
        {/* Main content column */}
        <div className="min-w-0">
          {/* Active filter indicator */}
          {filterRecipeName && (
            <div className="flex items-center gap-2 px-3 py-2.5 mb-4 rounded-lg bg-primary/10 border border-primary/30">
              <Filter className="flex-shrink-0 w-4 h-4 text-primary" />
              <span className="text-sm truncate text-primary">
                Filtering by: {getFilteruserName()}
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Clear recipe filter"
                onClick={() => setFilterRecipeName(null)}
                className="ml-auto text-primary"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          )}

          {/* Categories list - full page scroll */}
          <div className="space-y-4">
            {visibleCategories.map((category) => (
              <ShoppingCategory
                key={category}
                category={category}
                items={getFilteredItems(groupedItems[category])}
                onToggleItem={handleToggleItem}
                onToggleFlagged={handleToggleFlagged}
              />
            ))}
          </div>
        </div>

        {/* Recipe filter sidebar (desktop only) - sticky below header */}
        <div className="hidden lg:block">
          <div className="sticky top-28 transform-gpu">
            <IngredientSourceSidebar
              recipes={recipes}
              manualItemCount={manualItemCount}
              manualCollectedCount={manualCollectedCount}
              activeFilter={filterRecipeName}
              onFilterChange={setFilterRecipeName}
            />
          </div>
        </div>
      </div>

      {/* Clear Manual Items Confirmation Dialog */}
      <AlertDialog open={showClearManualDialog} onOpenChange={setShowClearManualDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clear Manual Items?</AlertDialogTitle>
            <AlertDialogDescription>
              You have {manualItemCount - manualCollectedCount} unchecked manual item{manualItemCount - manualCollectedCount !== 1 ? 's' : ''} that will be deleted. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmClearManualItems}>
              Clear Items
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageLayout>
  );
}
