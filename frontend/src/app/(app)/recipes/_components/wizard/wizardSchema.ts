import { z } from "zod";
import { unitRequiresQuantity } from "@/lib/formValidation";

// ============================================================================
// Ingredient item schema with unit-aware validation
// ============================================================================

const wizardIngredientSchema = z
  .object({
    id: z.string(),
    ingredientName: z.string(),
    ingredientCategory: z.string(),
    quantity: z.string(),
    unit: z.string(),
    existingIngredientId: z.number().nullable().optional(),
  })
  .superRefine((ing, ctx) => {
    // Skip completely empty rows
    if (!ing.ingredientName.trim() && !ing.quantity.trim() && !ing.unit) {
      return;
    }

    // Name validation
    if (!ing.ingredientName.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Ingredient name is required",
        path: ["ingredientName"],
      });
    } else if (ing.ingredientName.trim().length > 200) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Name must be at most 200 characters",
        path: ["ingredientName"],
      });
    }

    // Quantity validation (unit-aware)
    const qty = ing.quantity.trim() ? parseFloat(ing.quantity) : null;
    if (unitRequiresQuantity(ing.unit)) {
      if (qty === null || Number.isNaN(qty)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Quantity required for this unit",
          path: ["quantity"],
        });
      } else if (qty < 0) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Quantity must be at least 0",
          path: ["quantity"],
        });
      }
    } else if (qty !== null && !Number.isNaN(qty) && qty < 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Quantity must be at least 0",
        path: ["quantity"],
      });
    }
  });

// ============================================================================
// Direction item schema
// ============================================================================

const wizardDirectionSchema = z.object({
  id: z.string(),
  text: z.string(),
});

// ============================================================================
// Main wizard form schema
// ============================================================================

export const wizardFormSchema = z.object({
  // Recipe basics
  recipeName: z
    .string()
    .min(1, "Recipe name is required")
    .max(255, "Recipe name must be at most 255 characters"),
  description: z.string(),
  prepTime: z.number().int().min(0, "Prep time must be at least 0"),
  cookTime: z.number().int().min(0, "Cook time must be at least 0"),
  servings: z.number().int().min(1, "Servings must be at least 1"),
  difficulty: z.string(),
  mealType: z.string().min(1, "Meal type is required"),
  category: z.string().min(1, "Category is required"),
  dietaryPreference: z.string(),

  // Ingredients
  ingredients: z.array(wizardIngredientSchema),

  // Directions
  directions: z.array(wizardDirectionSchema),

  // Notes
  notes: z.string(),
});

export type WizardFormValues = z.infer<typeof wizardFormSchema>;

// ============================================================================
// Step-to-field mapping for partial validation via form.trigger()
// ============================================================================

export const WIZARD_STEP_FIELDS: Record<number, (keyof WizardFormValues)[]> = {
  2: ["recipeName", "category", "mealType", "prepTime", "cookTime", "servings"],
  3: ["ingredients"],
  4: ["directions"],
};
