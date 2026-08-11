"use client";

import { useCallback, useId } from "react";
import { useFormContext } from "react-hook-form";
import {
  Flame,
  Loader2,
  Sparkles,
  Trash2,
  UtensilsCrossed,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useEstimateNutrition } from "@/hooks/api/useAI";
import type { NutritionFactsDTO } from "@/types/ai";
import type { WizardFormValues } from "../wizardSchema";

// ============================================================================
// Props (only non-form state — form data via useFormContext)
// ============================================================================

interface NutritionStepProps {
  nutritionFacts: NutritionFactsDTO | null;
  onNutritionChange: (facts: NutritionFactsDTO | null) => void;
}

/** Default empty nutrition facts for manual editing. */
const EMPTY_NUTRITION: NutritionFactsDTO = {
  calories: null,
  protein_g: null,
  total_fat_g: null,
  saturated_fat_g: null,
  trans_fat_g: null,
  cholesterol_mg: null,
  sodium_mg: null,
  total_carbs_g: null,
  dietary_fiber_g: null,
  total_sugars_g: null,
  is_ai_estimated: false,
};

/** Max daily values used for macronutrient progress bar percentages. */
const MACRO_MAX = {
  protein_g: 50,
  total_carbs_g: 300,
  total_fat_g: 65,
} as const;

/** Shared className for large transparent number inputs. */
const LARGE_INPUT_CLASS =
  "h-auto border-0 bg-transparent p-0 shadow-none focus-visible:ring-0 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none";

// ============================================================================
// NutritionStep
// ============================================================================

export function NutritionStep({
  nutritionFacts,
  onNutritionChange,
}: NutritionStepProps) {
  const form = useFormContext<WizardFormValues>();
  const recipeName = form.watch("recipeName");
  const ingredients = form.watch("ingredients");
  const servings = form.watch("servings");

  const estimateMutation = useEstimateNutrition();
  const fieldIdPrefix = useId();

  const canEstimate =
    recipeName.trim().length > 0 &&
    ingredients.some((ing) => ing.ingredientName.trim().length > 0);

  // ── Helpers ──────────────────────────────────────────────────────────────

  /** Ensure we always have a NutritionFactsDTO to mutate (lazy-create on first edit). */
  const getOrCreate = useCallback((): NutritionFactsDTO => {
    return nutritionFacts ?? { ...EMPTY_NUTRITION };
  }, [nutritionFacts]);

  /** Update a single numeric nutrition field. */
  const handleFieldChange = useCallback(
    (key: keyof NutritionFactsDTO, raw: string) => {
      const updated = { ...getOrCreate() };
      if (raw.trim() === "") {
        (updated[key] as number | null) = null;
      } else {
        const parsed = parseFloat(raw);
        (updated[key] as number | null) = Number.isNaN(parsed) ? null : parsed;
      }
      onNutritionChange(updated);
    },
    [getOrCreate, onNutritionChange]
  );

  /** Format a numeric field value for display in an input. */
  const fieldValue = (key: keyof NutritionFactsDTO): string => {
    const val = nutritionFacts?.[key];
    if (val === null || val === undefined || typeof val === "boolean") return "";
    return String(val);
  };

  /** Calculate progress bar percentage for a macronutrient. */
  const macroPercent = (key: keyof typeof MACRO_MAX): number => {
    const val = nutritionFacts?.[key];
    if (val === null || val === undefined || typeof val === "boolean") return 0;
    return Math.min(100, Math.round((Number(val) / MACRO_MAX[key]) * 100));
  };

  // ── AI Estimation ────────────────────────────────────────────────────────

  const handleEstimate = useCallback(() => {
    const validIngredients = ingredients
      .filter((ing) => ing.ingredientName.trim().length > 0)
      .map((ing) => ({
        ingredient_name: ing.ingredientName.trim(),
        quantity: ing.quantity.trim() ? parseFloat(ing.quantity) : null,
        unit: ing.unit || null,
      }));

    estimateMutation.mutate(
      {
        recipe_name: recipeName.trim(),
        ingredients: validIngredients,
        servings: servings || null,
      },
      {
        onSuccess: (data) => {
          if (data.success && data.nutrition_facts) {
            onNutritionChange(data.nutrition_facts);
          }
        },
      }
    );
  }, [recipeName, ingredients, servings, estimateMutation, onNutritionChange]);

  const handleClear = useCallback(() => {
    onNutritionChange(null);
  }, [onNutritionChange]);

  // ── Render ───────────────────────────────────────────────────────────────

  const servingsDisplay = servings || "—";

  return (
    <div className="space-y-4">
      {/* ── Header row ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between min-h-8">
        <p className="text-sm text-muted-foreground">
          Per serving &bull; All values are optional
        </p>
        <div className="flex items-center gap-2">
          {nutritionFacts?.is_ai_estimated && (
            <Badge variant="secondary">AI Estimated</Badge>
          )}
          {nutritionFacts && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleClear}
              aria-label="Clear nutrition facts"
            >
              <Trash2 className="size-4 mr-1.5" strokeWidth={1.5} />
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* ── Two-column layout ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* ── Left column: Calories, Servings, Macronutrients ──────────── */}
      <div className="space-y-4">
        {/* Calories + Servings row */}
        <div className="grid grid-cols-2 gap-4">
          {/* Calories card */}
          <Card className="border-border">
            <CardContent size="sm" className="pt-4 space-y-2">
              <div className="flex items-center gap-2">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary-surface">
                  <Flame className="size-4 text-primary-on-surface" strokeWidth={1.5} />
                </div>
                <Label
                  htmlFor={`${fieldIdPrefix}-calories`}
                  size="sm"
                  className="text-muted-foreground font-normal"
                >
                  Calories
                </Label>
              </div>
              <div className="flex items-baseline justify-between">
                <Input
                  id={`${fieldIdPrefix}-calories`}
                  type="number"
                  placeholder="0"
                  value={fieldValue("calories")}
                  onChange={(e) => handleFieldChange("calories", e.target.value)}
                  className={`${LARGE_INPUT_CLASS} w-24 text-4xl font-bold text-foreground`}
                  min={0}
                />
                <span className="text-sm text-muted-foreground">kcal</span>
              </div>
              <p className="text-xs text-muted-foreground">Per serving</p>
            </CardContent>
          </Card>

          {/* Servings card */}
          <Card className="border-border">
            <CardContent size="sm" className="pt-4 space-y-2">
              <div className="flex items-center gap-2">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-secondary-surface">
                  <UtensilsCrossed className="size-4 text-secondary-on-surface" strokeWidth={1.5} />
                </div>
                <Label
                  size="sm"
                  className="text-muted-foreground font-normal"
                >
                  Servings
                </Label>
              </div>
              <div className="flex items-baseline justify-between">
                <p className="text-4xl font-bold text-foreground">
                  {servingsDisplay}
                </p>
                <span className="text-sm text-muted-foreground">ppl</span>
              </div>
              <p className="text-xs text-muted-foreground">Yields</p>
            </CardContent>
          </Card>
        </div>

        {/* ─── Macronutrients ────────────────────────────────────────── */}
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Macronutrients
          </p>
          <div className="grid grid-cols-3 gap-3">
            <MacroCard
              fieldIdPrefix={fieldIdPrefix}
              label="Protein"
              fieldKey="protein_g"
              unit="g"
              color="bg-info"
              trackColor="bg-info/20"
              percent={macroPercent("protein_g")}
              value={fieldValue("protein_g")}
              onChange={(v) => handleFieldChange("protein_g", v)}
            />
            <MacroCard
              fieldIdPrefix={fieldIdPrefix}
              label="Carbs"
              fieldKey="total_carbs_g"
              unit="g"
              color="bg-success"
              trackColor="bg-success/20"
              percent={macroPercent("total_carbs_g")}
              value={fieldValue("total_carbs_g")}
              onChange={(v) => handleFieldChange("total_carbs_g", v)}
            />
            <MacroCard
              fieldIdPrefix={fieldIdPrefix}
              label="Fats"
              fieldKey="total_fat_g"
              unit="g"
              color="bg-warning"
              trackColor="bg-warning/20"
              percent={macroPercent("total_fat_g")}
              value={fieldValue("total_fat_g")}
              onChange={(v) => handleFieldChange("total_fat_g", v)}
            />
          </div>
        </div>
      </div>

      {/* ── Right column: Detailed Facts ─────────────────────────────── */}
        <Card className="border-border">
          <CardContent size="sm" className="pt-4 space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Detailed Facts
            </p>

            <DetailRow
              fieldIdPrefix={fieldIdPrefix}
              label="Saturated Fat"
              fieldKey="saturated_fat_g"
              unit="g"
              value={fieldValue("saturated_fat_g")}
              onChange={(v) => handleFieldChange("saturated_fat_g", v)}
            />
            <DetailRow
              fieldIdPrefix={fieldIdPrefix}
              label="Trans Fat"
              fieldKey="trans_fat_g"
              unit="g"
              value={fieldValue("trans_fat_g")}
              onChange={(v) => handleFieldChange("trans_fat_g", v)}
            />

            <Separator />

            <DetailRow
              fieldIdPrefix={fieldIdPrefix}
              label="Cholesterol"
              fieldKey="cholesterol_mg"
              unit="mg"
              value={fieldValue("cholesterol_mg")}
              onChange={(v) => handleFieldChange("cholesterol_mg", v)}
            />
            <DetailRow
              fieldIdPrefix={fieldIdPrefix}
              label="Sodium"
              fieldKey="sodium_mg"
              unit="mg"
              value={fieldValue("sodium_mg")}
              onChange={(v) => handleFieldChange("sodium_mg", v)}
            />

            <Separator />

            <DetailRow
              fieldIdPrefix={fieldIdPrefix}
              label="Fiber"
              fieldKey="dietary_fiber_g"
              unit="g"
              value={fieldValue("dietary_fiber_g")}
              onChange={(v) => handleFieldChange("dietary_fiber_g", v)}
            />
            <DetailRow
              fieldIdPrefix={fieldIdPrefix}
              label="Sugar"
              fieldKey="total_sugars_g"
              unit="g"
              value={fieldValue("total_sugars_g")}
              onChange={(v) => handleFieldChange("total_sugars_g", v)}
            />

            {/* ── AI Estimation ───────────────────────────────────────── */}
            {estimateMutation.isError && (
              <div role="alert" aria-live="assertive">
                <p className="text-sm text-destructive">
                  {estimateMutation.error instanceof Error && estimateMutation.error.message
                    ? estimateMutation.error.message
                    : "Failed to estimate nutrition. Please try again."}
                </p>
              </div>
            )}

            <Button
              type="button"
              variant="outline"
              onClick={handleEstimate}
              disabled={!canEstimate || estimateMutation.isPending}
              className="w-full"
            >
              {estimateMutation.isPending ? (
                <>
                  <Loader2
                    className="size-4 mr-2 animate-spin"
                    strokeWidth={1.5}
                  />
                  <span className="sr-only">Estimating nutrition facts</span>
                  Estimating...
                </>
              ) : (
                <>
                  <Sparkles className="size-4 mr-2" strokeWidth={1.5} />
                  Calculate with AI
                </>
              )}
            </Button>

            {!canEstimate && !nutritionFacts && (
              <p className="text-xs text-center text-muted-foreground">
                Add a recipe name and ingredients first.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

interface MacroCardProps {
  fieldIdPrefix: string;
  label: string;
  fieldKey: string;
  unit: string;
  color: string;
  trackColor: string;
  percent: number;
  value: string;
  onChange: (value: string) => void;
}

function MacroCard({
  fieldIdPrefix,
  label,
  fieldKey,
  unit,
  color,
  trackColor,
  percent,
  value,
  onChange,
}: MacroCardProps) {
  const inputId = `${fieldIdPrefix}-${fieldKey}`;

  return (
    <Card className="border-border">
      <CardContent size="sm" className="pt-3 pb-3 space-y-2">
        <Label htmlFor={inputId} size="sm" className="text-muted-foreground font-normal">
          {label}
        </Label>
        <div className="flex items-baseline justify-between">
          <Input
            id={inputId}
            type="number"
            placeholder="0"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className={`${LARGE_INPUT_CLASS} w-12 text-2xl font-bold text-foreground`}
            min={0}
          />
          <span className="text-sm text-muted-foreground">{unit}</span>
        </div>
        {/* Progress bar */}
        <div className={`relative h-2 w-full overflow-hidden rounded-full ${trackColor}`}>
          <div
            className={`h-full rounded-full transition-all duration-300 ease-out ${color}`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}

interface DetailRowProps {
  fieldIdPrefix: string;
  label: string;
  fieldKey: string;
  unit: string;
  value: string;
  onChange: (value: string) => void;
}

function DetailRow({
  fieldIdPrefix,
  label,
  fieldKey,
  unit,
  value,
  onChange,
}: DetailRowProps) {
  const inputId = `${fieldIdPrefix}-${fieldKey}`;

  return (
    <div className="flex items-center justify-between">
      <Label htmlFor={inputId} size="sm">
        {label}
      </Label>
      <div className="flex items-baseline gap-1">
        <Input
          id={inputId}
          type="number"
          size="sm"
          placeholder="0"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-16 text-right"
          min={0}
        />
        <span className="text-xs text-muted-foreground w-6">{unit}</span>
      </div>
    </div>
  );
}
