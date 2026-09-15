"use client";

import { useFormContext } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { NumberStepper } from "@/components/ui/numeric-stepper";
import { MEAL_TYPE_OPTIONS, DIETARY_PREFERENCES } from "@/lib/constants";
import { useCategoryOptions } from "@/hooks/api";
import { ImageUploadCard } from "@/app/(app)/recipes/_components/shared/ImageUploadCard";
import type { WizardFormValues } from "../wizardSchema";

// ============================================================================
// Props (image handlers only — form data via useFormContext)
// ============================================================================

interface RecipeBasicsStepProps {
  imagePreview: string | null;
  isAiGenerated: boolean;
  onImageUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onGeneratedImageAccept: (
    refBase64: string,
    refDataUrl: string,
    bannerBase64?: string
  ) => void;
  onBannerOnlyAccept: (bannerBase64: string) => void;
}

// ============================================================================
// Component
// ============================================================================

export function RecipeBasicsStep({
  imagePreview,
  isAiGenerated,
  onImageUpload,
  onGeneratedImageAccept,
  onBannerOnlyAccept,
}: RecipeBasicsStepProps) {
  const form = useFormContext<WizardFormValues>();
  const { formOptions: categoryOptions } = useCategoryOptions();

  const recipeName = form.watch("recipeName");

  return (
    /*
      Layout: flex row with fixed-width image column + fluid form column.
      On mobile (<md), stacks vertically with image centered.
    */
    <div className="flex flex-col md:flex-row gap-6">
      {/* ── Left column — Image (fixed width, 1:1 aspect ratio) ───── */}
      <div className="w-full md:w-60 shrink-0 overflow-hidden">
        <ImageUploadCard
          recipeName={recipeName}
          imagePreview={imagePreview}
          isAiGenerated={isAiGenerated}
          onImageUpload={onImageUpload}
          onGeneratedImageAccept={onGeneratedImageAccept}
          onBannerOnlyAccept={onBannerOnlyAccept}
          compact
        />
      </div>

      {/* ── Right column — All form fields ────────────────────────── */}
      <div className="flex-1 min-w-0 space-y-4">
        {/* Recipe Title */}
        <FormField
          control={form.control}
          name="recipeName"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                Recipe Title <span className="text-destructive">*</span>
              </FormLabel>
              <FormControl>
                <Input
                  {...field}
                  placeholder="e.g. Grandma's Chocolate Chip Cookies"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Description */}
        <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  {...field}
                  placeholder="A brief description of your recipe..."
                  rows={3}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Prep / Cook / Servings — 3-column row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <FormField
            control={form.control}
            name="prepTime"
            render={({ field, fieldState }) => (
              <FormItem>
                <FormControl>
                  <NumberStepper
                    value={field.value}
                    onChange={field.onChange}
                    min={0}
                    max={999}
                    step={5}
                    unit="min"
                    label="Prep Time"
                    hasError={!!fieldState.error}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="cookTime"
            render={({ field, fieldState }) => (
              <FormItem>
                <FormControl>
                  <NumberStepper
                    value={field.value}
                    onChange={field.onChange}
                    min={0}
                    max={999}
                    step={5}
                    unit="min"
                    label="Cook Time"
                    hasError={!!fieldState.error}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="servings"
            render={({ field, fieldState }) => (
              <FormItem>
                <FormControl>
                  <NumberStepper
                    value={field.value}
                    onChange={field.onChange}
                    min={1}
                    max={99}
                    step={1}
                    label="Servings"
                    hasError={!!fieldState.error}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Difficulty / Category — 2-column row */}
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="difficulty"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Difficulty</FormLabel>
                  <ToggleGroup
                    type="single"
                    variant="outline"
                    value={field.value}
                    onValueChange={field.onChange}
                    aria-label="Recipe difficulty"
                    className="w-full"
                  >
                    <ToggleGroupItem value="Easy" className="flex-1">Easy</ToggleGroupItem>
                    <ToggleGroupItem value="Medium" className="flex-1">Med</ToggleGroupItem>
                    <ToggleGroupItem value="Hard" className="flex-1">Hard</ToggleGroupItem>
                  </ToggleGroup>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="category"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Category <span className="text-destructive">*</span>
                </FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent portal>
                    {categoryOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Meal Type / Dietary — 2-column row */}
        <div className="grid grid-cols-2 gap-3">
          <FormField
            control={form.control}
            name="mealType"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Meal Type</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent portal>
                    {MEAL_TYPE_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="dietaryPreference"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dietary Preference</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent portal>
                    {DIETARY_PREFERENCES.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </div>
    </div>
  );
}
