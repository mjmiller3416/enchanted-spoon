"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp, Loader2, Plus, X } from "lucide-react";
import { useCreateMeal, useUpdateMeal, useAddToPlanner } from "@/hooks/api";
import { useUnsavedChanges } from "@/hooks/ui/useUnsavedChanges";
import { RecipeBrowserView } from "@/components/recipe/RecipeBrowserView";
import { MealPreviewPanel } from "./MealPreviewPanel";
import { SavedView } from "./SavedView";
import { mapCardDtoToCardData } from "@/lib/recipeCardMapper";
import type { RecipeCardData } from "@/types/recipe";
import type { MealSelectionResponseDTO } from "@/types/meal";
import type { PlannerEntryResponseDTO } from "@/types/planner";

interface MealCreationOverlayProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** "create" builds a new meal; "edit" updates an existing one */
  mode?: "create" | "edit";
  /** Edit mode: id of the meal being edited */
  editingMealId?: number | null;
  /** Edit mode: original meal name, preserved through recipe swaps */
  editingMealName?: string | null;
  /** Initial selections (edit mode prefill) */
  initialMain?: RecipeCardData | null;
  initialSides?: RecipeCardData[];
  /** Called with the new planner entry after a meal is created/added */
  onEntryCreated?: (entry: PlannerEntryResponseDTO) => void;
  /** Called after an edit is saved */
  onMealUpdated?: () => void;
}

/** Snapshot of a saved meal loaded into the builder, so an unmodified
 *  confirm can reuse the saved meal instead of duplicating it. */
interface SavedMealSnapshot {
  mealId: number;
  mainId: number | null;
  sideIds: number[];
}

const sameIdSet = (a: Array<string | number>, b: Array<string | number>) => {
  if (a.length !== b.length) return false;
  const bSet = new Set(b.map(Number));
  return a.every((id) => bSet.has(Number(id)));
};

/**
 * MealCreationOverlay — the single meal-builder surface.
 *
 * Two-panel dialog on desktop (live meal preview + recipe browser / saved
 * meals side by side); on mobile the browser fills the dialog with a sticky
 * summary bar at the bottom. Handles both creating a new meal and editing an
 * existing one, with discard confirmation and browser-navigation guards
 * while a meal is in progress.
 */
export function MealCreationOverlay({
  open,
  onOpenChange,
  mode = "create",
  editingMealId = null,
  editingMealName = null,
  initialMain = null,
  initialSides,
  onEntryCreated,
  onMealUpdated,
}: MealCreationOverlayProps) {
  const createMealMutation = useCreateMeal();
  const updateMealMutation = useUpdateMeal();
  const addToPlannerMutation = useAddToPlanner();

  const [pickerMode, setPickerMode] = useState<"main" | "side">("main");
  const [pendingMain, setPendingMain] = useState<RecipeCardData | null>(null);
  const [pendingSides, setPendingSides] = useState<RecipeCardData[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDiscardDialog, setShowDiscardDialog] = useState(false);
  const [rightPanelTab, setRightPanelTab] = useState<string>("browse");
  const [mobilePreviewOpen, setMobilePreviewOpen] = useState(false);
  const [savedSnapshot, setSavedSnapshot] = useState<SavedMealSnapshot | null>(null);

  const isEdit = mode === "edit";

  // Initialize builder state when the dialog opens (prefilled in edit mode)
  const wasOpenRef = useRef(false);
  useEffect(() => {
    if (open && !wasOpenRef.current) {
      setPendingMain(initialMain ?? null);
      setPendingSides(initialSides ?? []);
      setPickerMode(initialMain ? "side" : "main");
      setRightPanelTab("browse");
      setMobilePreviewOpen(false);
      setSavedSnapshot(null);
      setShowDiscardDialog(false);
    }
    wasOpenRef.current = open;
  }, [open, initialMain, initialSides]);

  // Dirty = anything worth confirming before it's thrown away
  const isDirty = useMemo(() => {
    if (!open) return false;
    if (isEdit) {
      const initialIds = (initialSides ?? []).map((s) => s.id);
      return (
        Number(pendingMain?.id) !== Number(initialMain?.id) ||
        !sameIdSet(pendingSides.map((s) => s.id), initialIds)
      );
    }
    return !!pendingMain || pendingSides.length > 0;
  }, [open, isEdit, pendingMain, pendingSides, initialMain, initialSides]);

  const closeOverlay = useCallback(() => {
    setShowDiscardDialog(false);
    onOpenChange(false);
  }, [onOpenChange]);

  // Browser back / refresh / SafeLink protection while a meal is in progress
  const { showLeaveDialog, setShowLeaveDialog, confirmLeave, cancelLeave } =
    useUnsavedChanges({
      isDirty,
      onConfirmLeave: closeOverlay,
    });

  // --- Dialog close with discard guard ---

  const handleDialogOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && isDirty) {
      setShowDiscardDialog(true);
    } else if (!nextOpen) {
      closeOverlay();
    }
  };

  // --- Meal preview panel handlers ---

  const handleSelectMain = () => {
    setPickerMode("main");
    setRightPanelTab("browse");
  };

  const handleAddSides = () => {
    setPickerMode("side");
    setRightPanelTab("browse");
  };

  const handleRemoveMain = () => {
    setPendingMain(null);
    setPendingSides([]);
    setSavedSnapshot(null);
    setPickerMode("main");
  };

  const handleRemoveSide = (recipeId: number) => {
    setPendingSides((prev) => prev.filter((s) => Number(s.id) !== recipeId));
  };

  // --- Recipe browser handlers ---

  const handleRecipeSelect = (recipe: RecipeCardData) => {
    if (pickerMode === "main") {
      setPendingMain(recipe);
      setPickerMode("side");
    } else {
      setPendingSides((prev) => {
        const isSelected = prev.some((s) => s.id === recipe.id);
        if (isSelected) return prev.filter((s) => s.id !== recipe.id);
        if (prev.length >= 3) return prev;
        return [...prev, recipe];
      });
    }
  };

  // --- Saved meals: load into the builder for review/tweaks ---

  const handleSavedMealSelected = (meal: MealSelectionResponseDTO) => {
    setPendingMain(meal.main_recipe ? mapCardDtoToCardData(meal.main_recipe) : null);
    setPendingSides(meal.side_recipes.map(mapCardDtoToCardData));
    setSavedSnapshot({
      mealId: meal.id,
      mainId: meal.main_recipe?.id ?? null,
      sideIds: meal.side_recipes.map((r) => r.id),
    });
    setRightPanelTab("browse");
    setPickerMode("side");
  };

  // --- Confirm / Save ---

  const handleConfirmMeal = async () => {
    if (!pendingMain) return;

    setIsSubmitting(true);
    try {
      const sideRecipeIds = pendingSides.map((r) => Number(r.id));

      if (isEdit && editingMealId) {
        await updateMealMutation.mutateAsync({
          mealId: editingMealId,
          data: {
            meal_name: editingMealName || pendingMain.name,
            main_recipe_id: Number(pendingMain.id),
            side_recipe_ids: sideRecipeIds,
          },
        });
        onMealUpdated?.();
        closeOverlay();
        return;
      }

      // A saved meal loaded and left unmodified goes straight to the planner —
      // reusing the saved meal instead of creating a duplicate copy of it
      const reuseSavedMeal =
        savedSnapshot &&
        Number(pendingMain.id) === Number(savedSnapshot.mainId) &&
        sameIdSet(sideRecipeIds, savedSnapshot.sideIds);

      let mealId: number;
      if (reuseSavedMeal) {
        mealId = savedSnapshot.mealId;
      } else {
        const meal = await createMealMutation.mutateAsync({
          meal_name: pendingMain.name,
          main_recipe_id: Number(pendingMain.id),
          side_recipe_ids: sideRecipeIds,
        });
        mealId = meal.id;
      }

      const entry = await addToPlannerMutation.mutateAsync(mealId);
      onEntryCreated?.(entry);
      closeOverlay();
    } catch (err) {
      console.error("Failed to save meal:", err);
      const message = err instanceof Error ? err.message : "Failed to save meal";
      if (message.includes("maximum capacity")) {
        toast.error("Meal queue is full", {
          description: "Remove a planned meal to make room for more.",
        });
      } else {
        toast.error(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // --- Discard ---

  const handleConfirmDiscard = () => {
    setShowDiscardDialog(false);
    closeOverlay();
  };

  const filterPortalRef = useRef<HTMLDivElement>(null);

  const selectedSideIds = new Set<string | number>(pendingSides.map((s) => s.id));

  const title = isEdit ? "Edit Meal" : "Add Meal";
  const confirmText = isEdit ? "Save Changes" : "Add to Meal Queue";
  const submittingText = isEdit ? "Saving..." : "Adding...";

  const previewPanel = (
    <MealPreviewPanel
      mainDish={pendingMain}
      sides={pendingSides}
      onSelectMain={handleSelectMain}
      onRemoveMain={handleRemoveMain}
      onRemoveSide={handleRemoveSide}
      onAddSides={handleAddSides}
      onAddToQueue={handleConfirmMeal}
      isSubmitting={isSubmitting}
      showHeader={false}
      buttonText={confirmText}
      submittingText={submittingText}
    />
  );

  return (
    <>
      {open && (
        <Dialog open={open} onOpenChange={handleDialogOpenChange}>
          <DialogContent
            size="xl"
            showCloseButton={false}
            className="max-w-full h-dvh rounded-none sm:rounded-lg sm:max-w-[90vw] lg:max-w-6xl sm:h-[85vh] p-0 gap-0 overflow-hidden"
          >
            <DialogTitle className="sr-only">{title}</DialogTitle>
            <DialogDescription className="sr-only">
              {isEdit
                ? "Change the main dish and sides of this meal"
                : "Build a meal by selecting a main dish and up to 3 sides"}
            </DialogDescription>

            <div
              ref={filterPortalRef}
              className="flex h-full relative overflow-hidden"
            >
              {/* Left panel — meal preview (desktop only) */}
              <div className="hidden lg:flex w-80 shrink-0 border-r border-border flex-col">
                <div className="px-5 pt-5 pb-3">
                  <h2 className="text-lg font-semibold">{title}</h2>
                  <p className="text-sm text-muted-foreground">
                    {isEdit ? "Adjust the main dish and sides" : "Build your perfect meal"}
                  </p>
                </div>
                <div className="flex-1 min-h-0 overflow-y-auto px-5 pb-5">
                  {previewPanel}
                </div>
              </div>

              {/* Right panel — recipe browser / saved meals */}
              <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <Tabs
                  value={rightPanelTab}
                  onValueChange={setRightPanelTab}
                  className="flex flex-col h-full"
                >
                  <div className="shrink-0 px-4 py-2 flex items-center gap-3">
                    {isEdit ? (
                      <h2 className="text-base font-semibold lg:hidden">{title}</h2>
                    ) : (
                      <TabsList>
                        <TabsTrigger value="browse">Browse Recipes</TabsTrigger>
                        <TabsTrigger value="saved">Saved Meals</TabsTrigger>
                      </TabsList>
                    )}
                    <span className="hidden sm:inline text-xs text-muted-foreground">
                      {pickerMode === "main"
                        ? "Select a main dish"
                        : `Selecting sides (${pendingSides.length}/3)`}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Close meal builder"
                      className="ml-auto"
                      onClick={() => handleDialogOpenChange(false)}
                    >
                      <X className="h-4 w-4" strokeWidth={1.5} />
                    </Button>
                  </div>

                  <TabsContent
                    value="browse"
                    className="relative flex-1 min-h-0 mt-0"
                    forceMount={rightPanelTab === "browse" ? undefined : true}
                    hidden={rightPanelTab !== "browse"}
                  >
                    <div className="absolute inset-0 overflow-y-auto [&_[data-sticky-header]]:top-0 [&_[data-sticky-header]]:md:top-0">
                      <RecipeBrowserView
                        key={pickerMode}
                        mode="select"
                        onSelect={handleRecipeSelect}
                        selectedIds={
                          pickerMode === "main"
                            ? pendingMain
                              ? new Set([pendingMain.id])
                              : new Set()
                            : selectedSideIds
                        }
                        filterMealType={pickerMode}
                        heroTitle={
                          pickerMode === "main"
                            ? "Select a Main Dish"
                            : "Select Side Dishes"
                        }
                        heroDescription={
                          pickerMode === "main"
                            ? "Choose the main dish for your meal"
                            : "Choose up to 3 side dishes"
                        }
                        filterPortalTarget={filterPortalRef}
                      />
                    </div>
                  </TabsContent>

                  {!isEdit && (
                    <TabsContent
                      value="saved"
                      className="relative flex-1 min-h-0 mt-0"
                    >
                      <div className="absolute inset-0 overflow-y-auto p-4">
                        <SavedView onMealSelected={handleSavedMealSelected} />
                      </div>
                    </TabsContent>
                  )}

                  {/* Mobile summary bar — sticky at the bottom, expandable preview */}
                  <div className="lg:hidden shrink-0 border-t border-border bg-card">
                    {mobilePreviewOpen && (
                      <div className="max-h-[45vh] overflow-y-auto px-4 pt-4 border-b border-border">
                        {previewPanel}
                      </div>
                    )}
                    <div className="flex items-center gap-3 px-4 py-3 pb-[max(env(safe-area-inset-bottom,0px),0.75rem)]">
                      <button
                        onClick={() => setMobilePreviewOpen((v) => !v)}
                        className="flex-1 min-w-0 text-left"
                        aria-expanded={mobilePreviewOpen}
                        aria-label={
                          mobilePreviewOpen ? "Hide meal preview" : "Show meal preview"
                        }
                      >
                        <p className="text-sm font-medium text-foreground truncate flex items-center gap-1.5">
                          {pendingMain ? pendingMain.name : "No main dish yet"}
                          {mobilePreviewOpen ? (
                            <ChevronDown className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} />
                          ) : (
                            <ChevronUp className="size-4 shrink-0 text-muted-foreground" strokeWidth={1.5} />
                          )}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Sides {pendingSides.length}/3 · tap to review
                        </p>
                      </button>
                      <Button
                        onClick={handleConfirmMeal}
                        disabled={!pendingMain || isSubmitting}
                        className="shrink-0"
                      >
                        {isSubmitting ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <Plus className="size-4" strokeWidth={1.5} />
                        )}
                        {isEdit ? "Save" : "Add"}
                      </Button>
                    </div>
                  </div>
                </Tabs>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Discard confirmation — dialog close attempts */}
      <AlertDialog open={showDiscardDialog} onOpenChange={setShowDiscardDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {isEdit ? "Discard changes?" : "Discard meal?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {isEdit
                ? "You have unsaved changes to this meal. Are you sure you want to discard them?"
                : "You have an unsaved meal in progress. Are you sure you want to discard it?"}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep Editing</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDiscard}>
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Leave confirmation — browser navigation while building */}
      <AlertDialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {isEdit ? "Discard changes?" : "Discard meal?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {isEdit
                ? "You have unsaved changes to this meal. Are you sure you want to leave?"
                : "You have a meal in progress. Are you sure you want to leave? Your selection will be lost."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={cancelLeave}>Keep Editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmLeave}
              className="bg-destructive hover:bg-destructive/90"
            >
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
