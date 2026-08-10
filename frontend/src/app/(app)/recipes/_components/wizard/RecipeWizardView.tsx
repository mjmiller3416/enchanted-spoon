"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Link, Loader2, RotateCcw, Save, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
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
import { Form } from "@/components/ui/form";
import { useCategories } from "@/hooks/api/useCategories";
import type { RecipeGenerationResponseDTO } from "@/types/ai";
import { useRecipeWizard } from "./useRecipeWizard";
import {
  MethodSelectionStep,
  RecipeBasicsStep,
  IngredientsStep,
  DirectionsNotesStep,
  NutritionStep,
  AIGenerateStep,
  UrlImportStep,
} from "./steps";

// ============================================================================
// Constants
// ============================================================================

const STEP_TITLES = [
  "Choose Method",
  "Recipe Basics",
  "Ingredients",
  "Directions & Notes",
  "Nutrition Facts",
];

const TOTAL_STEPS = 5;

// ============================================================================
// Props
// ============================================================================

interface RecipeWizardViewProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** "create" (default) or "edit" an existing recipe. */
  mode?: "create" | "edit";
  /** Recipe to load when mode is "edit". */
  recipeId?: number | null;
  /** Generated recipe to pre-fill a create-mode wizard (e.g. from the Genie). */
  initialGenerated?: RecipeGenerationResponseDTO | null;
}

// ============================================================================
// RecipeWizardView
// ============================================================================

export function RecipeWizardView({
  open,
  onOpenChange,
  mode = "create",
  recipeId = null,
  initialGenerated = null,
}: RecipeWizardViewProps) {
  const { data: categories = [], isLoading: categoriesLoading } = useCategories();

  const handleSave = useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  const wizard = useRecipeWizard({ onSave: handleSave, mode, recipeId, initialGenerated });
  const { currentStep, resetWizard, isEditMode, isLoadingRecipe } = wizard;

  // In edit mode the method-selection step (1) is skipped, so the visible
  // steps are 2–5 — re-base the counter/progress to that range.
  const totalVisibleSteps = isEditMode ? TOTAL_STEPS - 1 : TOTAL_STEPS;
  const displayStep = isEditMode ? currentStep - 1 : currentStep;
  const progressPercent = ((displayStep - 1) / (totalVisibleSteps - 1)) * 100;

  // Suppress transition-all on form inputs during step changes so
  // elements don't animate from their initial state on mount.
  const contentRef = useRef<HTMLDivElement>(null);
  const prevStepRef = useRef(currentStep);

  useEffect(() => {
    if (prevStepRef.current !== currentStep) {
      prevStepRef.current = currentStep;
      const el = contentRef.current;
      if (!el) return;
      el.classList.add("no-transition");
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          el.classList.remove("no-transition");
        });
      });
    }
  }, [currentStep]);

  const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);
  // Whether confirming the prompt should also close the wizard ("close",
  // from the X / Escape / backdrop / Cancel) or just return to step 1 and
  // stay open ("reset", from the footer "Start over" button).
  const [discardIntent, setDiscardIntent] = useState<"close" | "reset">("reset");

  // Request to close the wizard (X / Escape / backdrop / step-1 Cancel).
  // Only prompt when there's actually unsaved data to lose; otherwise reset
  // and close so reopening starts fresh at the feature-select step.
  const handleRequestClose = useCallback(() => {
    if (wizard.hasUnsavedData) {
      setDiscardIntent("close");
      setShowDiscardConfirm(true);
      return;
    }
    resetWizard();
    onOpenChange(false);
  }, [wizard.hasUnsavedData, resetWizard, onOpenChange]);

  // Radix fires onOpenChange(false) for the X button, Escape, and backdrop.
  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (nextOpen) {
        onOpenChange(true);
        return;
      }
      handleRequestClose();
    },
    [onOpenChange, handleRequestClose]
  );

  // Footer "Start over" (steps 2+): wipe inputs, stay open at step 1.
  const handleStartOverClick = useCallback(() => {
    if (!wizard.hasUnsavedData) {
      resetWizard();
      return;
    }
    setDiscardIntent("reset");
    setShowDiscardConfirm(true);
  }, [wizard.hasUnsavedData, resetWizard]);

  const handleDiscardConfirm = useCallback(() => {
    setShowDiscardConfirm(false);
    resetWizard();
    if (discardIntent === "close") {
      onOpenChange(false);
    }
  }, [discardIntent, resetWizard, onOpenChange]);

  return (
    <>
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {/*
        Layout: fixed-height flex column with 3 zones.
        ─────────────────────────────────────
        │  Header  (shrink-0)               │
        ├───────────────────────────────────┤
        │  Scrollable step content (flex-1) │
        ├───────────────────────────────────┤
        │  Footer nav (shrink-0)            │
        ─────────────────────────────────────

        NOTE: If your DialogContent already applies padding/gap via
        shadcn defaults, add these overrides to your dialog.tsx
        variant instead of using !important here:
          - padding: 0
          - gap: 0
          - display: flex / flex-direction: column
      */}
      <DialogContent
        size="xl"
        className="flex flex-col h-[85vh] p-0 gap-0 overflow-hidden"
      >
        {/* ── Header ──────────────────────────────────────────────── */}
        <div className="shrink-0 px-6 pt-5 pb-4 space-y-3">
          <DialogHeader className="text-center sm:text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-primary">
              {isEditMode ? "Edit Recipe" : "Create New Recipe"}
            </p>
            <DialogTitle className="text-2xl font-bold">
              {wizard.currentStep === 2 && wizard.creationMethod === "ai-generate"
                ? "AI Recipe Generator"
                : wizard.currentStep === 2 && wizard.creationMethod === "url-import"
                  ? "Import from URL"
                  : STEP_TITLES[wizard.currentStep - 1]}
            </DialogTitle>
            <DialogDescription>
              Step {displayStep} of {totalVisibleSteps}
            </DialogDescription>
          </DialogHeader>

          {/* Dev: fill sample data (floating so it doesn't affect layout) */}
          {process.env.NODE_ENV === "development" && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={wizard.fillSampleData}
              className="absolute top-2 left-2 z-50 text-xs opacity-50 hover:opacity-100 transition-opacity"
            >
              Dev: Fill Sample Data
            </Button>
          )}

          {/* Progress bar */}
          <Progress value={progressPercent} className="h-1" />
        </div>

        {/* ── Scrollable step content ─────────────────────────────── */}
        <Form {...wizard.form}>
        <div
          ref={contentRef}
          className="flex-1 min-h-0 overflow-y-auto border-t border-border px-6 py-6"
        >
          {isLoadingRecipe && (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={1.5} />
            </div>
          )}

          {!isLoadingRecipe && wizard.currentStep === 1 && (
            <MethodSelectionStep
              selectedMethod={wizard.creationMethod}
              onSelect={(method) => {
                wizard.setCreationMethod(method);
                wizard.goToStep(2);
              }}
            />
          )}

          {wizard.currentStep === 2 && (
            wizard.creationMethod === "ai-generate" ? (
              categoriesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={1.5} />
                </div>
              ) : (
              <AIGenerateStep
                prompt={wizard.aiPrompt}
                setPrompt={wizard.setAiPrompt}
                preferences={wizard.aiPreferences}
                setPreferences={wizard.setAiPreferences}
                isGenerating={wizard.isGenerating}
                error={wizard.aiError}
                categories={categories}
              />
              )
            ) : wizard.creationMethod === "url-import" ? (
              <UrlImportStep
                url={wizard.importUrl}
                setUrl={wizard.setImportUrl}
                isImporting={wizard.isImporting}
                error={wizard.importError}
                onSubmit={wizard.handleWizardImport}
              />
            ) : (
              <RecipeBasicsStep
                imagePreview={wizard.imagePreview}
                isAiGenerated={wizard.imageIsAiGenerated}
                onImageUpload={wizard.handleImageUpload}
                onGeneratedImageAccept={wizard.handleGeneratedImageAccept}
                onBannerOnlyAccept={wizard.handleBannerOnlyAccept}
              />
            )
          )}

          {wizard.currentStep === 3 && (
            <IngredientsStep
              availableIngredients={wizard.availableIngredients}
            />
          )}

          {wizard.currentStep === 4 && (
            <DirectionsNotesStep />
          )}

          {wizard.currentStep === 5 && (
            <NutritionStep
              nutritionFacts={wizard.nutritionFacts}
              onNutritionChange={wizard.setNutritionFacts}
            />
          )}
        </div>
        </Form>

          {/* ── Footer navigation ───────────────────────────────────── */}
          <div className="flex w-full items-center justify-between px-6 py-4 border-t border-border-subtle bg-background/50">
            {/* Left side — Discard (steps 2+, create mode only) */}
            <div className="flex items-center min-h-10">
              {!isEditMode && currentStep > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleStartOverClick}
                  disabled={wizard.isSubmitting}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <RotateCcw className="size-3.5 mr-1.5" strokeWidth={1.5} />
                  Start over
                </Button>
              )}
            </div>

            {/* Right side — navigation buttons */}
            <div className="flex items-center gap-3">
              {/* Step 1: Cancel */}
              {currentStep === 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  className="px-8 font-normal"
                  onClick={handleRequestClose}
                >
                  Cancel
                </Button>
              )}

              {/* Steps 3+: Back */}
              {currentStep > 2 && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={wizard.prevStep}
                  disabled={wizard.isSubmitting}
                >
                  <ArrowLeft className="size-4 mr-2" strokeWidth={1.5} />
                  Back
                </Button>
              )}

              {/* Step 2 AI: Generate Recipe */}
              {currentStep === 2 && wizard.creationMethod === "ai-generate" && (
                <Button
                  type="button"
                  onClick={wizard.handleWizardGenerate}
                  disabled={!wizard.aiPrompt.trim() || wizard.isGenerating}
                >
                  {wizard.isGenerating ? (
                    <>
                      <Loader2 className="size-4 mr-2 animate-spin" strokeWidth={1.5} />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="size-4 mr-2" strokeWidth={1.5} />
                      Generate Recipe
                    </>
                  )}
                </Button>
              )}

              {/* Step 2 URL import: Import Recipe */}
              {currentStep === 2 && wizard.creationMethod === "url-import" && (
                <Button
                  type="button"
                  onClick={wizard.handleWizardImport}
                  disabled={!wizard.importUrl.trim() || wizard.isImporting}
                >
                  {wizard.isImporting ? (
                    <>
                      <Loader2 className="size-4 mr-2 animate-spin" strokeWidth={1.5} />
                      Importing...
                    </>
                  ) : (
                    <>
                      <Link className="size-4 mr-2" strokeWidth={1.5} />
                      Import Recipe
                    </>
                  )}
                </Button>
              )}

              {/* Steps 2-4: Next Step (not shown for AI generate / URL import steps) */}
              {currentStep > 1 && currentStep < TOTAL_STEPS && !(currentStep === 2 && (wizard.creationMethod === "ai-generate" || wizard.creationMethod === "url-import")) && (
                <Button
                  type="button"
                  onClick={wizard.nextStep}
                  disabled={!wizard.canProceed}
                >
                  Next Step
                  <ArrowRight className="size-4 ml-2" strokeWidth={1.5} />
                </Button>
              )}

              {/* Step 5: Save */}
              {currentStep === TOTAL_STEPS && (
                <Button
                  type="button"
                  onClick={wizard.handleSubmit}
                  disabled={wizard.isSubmitting}
                  aria-busy={wizard.isSubmitting}
                  aria-label={
                    wizard.isSubmitting
                      ? "Saving recipe..."
                      : isEditMode
                        ? "Save Changes"
                        : "Save Recipe"
                  }
                >
                  {wizard.isSubmitting ? <Loader2 className="size-4 mr-2 animate-spin" strokeWidth={1.5} /> : <Save className="size-4 mr-2" strokeWidth={1.5} />}
                  {wizard.isSubmitting ? "Saving..." : isEditMode ? "Save Changes" : "Save Recipe"}
                </Button>
              )}
            </div>
          </div>
      </DialogContent>
    </Dialog>

    <AlertDialog open={showDiscardConfirm} onOpenChange={setShowDiscardConfirm}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {isEditMode ? "Discard changes?" : "Discard this recipe?"}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {isEditMode
              ? "Your unsaved changes will be lost. This can't be undone."
              : "All progress will be lost. This can't be undone."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep Editing</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleDiscardConfirm}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            Discard
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
    </>
  );
}