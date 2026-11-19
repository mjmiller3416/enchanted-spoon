/**
 * Form Validation Utility
 *
 * A hybrid validation system that both normalizes input and returns validation errors.
 * Mirrors backend Pydantic patterns for consistency.
 */

// ============================================================================
// Core Types
// ============================================================================

/**
 * Result of validating and normalizing a field value.
 * Contains both the normalized value and any validation errors.
 */
export interface ValidationResult<T> {
  /** The normalized/transformed value (may differ from input) */
  value: T;
  /** Whether the value is valid */
  isValid: boolean;
  /** Human-readable error message, if invalid */
  error: string | null;
}

/**
 * A validator function that takes an input and returns a ValidationResult.
 * Validators both normalize the value AND check for errors.
 */
export type Validator<TInput, TOutput = TInput> = (
  input: TInput
) => ValidationResult<TOutput>;

/**
 * Configuration for field validation constraints.
 * Mirrors Pydantic Field() parameters.
 */
export interface FieldConstraints {
  /** Minimum length for strings, or minimum value for numbers */
  min?: number;
  /** Maximum length for strings, or maximum value for numbers */
  max?: number;
  /** Whether the field is required (non-empty/non-null) */
  required?: boolean;
  /** Regex pattern the value must match */
  pattern?: RegExp;
  /** Custom error message override */
  message?: string;
  /** Field label for error messages */
  label?: string;
}

// ============================================================================
// Result Helpers
// ============================================================================

/** Create a successful validation result */
export function valid<T>(value: T): ValidationResult<T> {
  return { value, isValid: true, error: null };
}

/** Create a failed validation result */
export function invalid<T>(value: T, error: string): ValidationResult<T> {
  return { value, isValid: false, error };
}

// ============================================================================
// String Validators
// ============================================================================

/**
 * Normalizes and validates a string field.
 * Automatically trims whitespace (like backend's mode="before" validators).
 */
export function validateString(
  input: string | null | undefined,
  constraints: FieldConstraints = {}
): ValidationResult<string> {
  const { min, max, required = false, pattern, message, label = "Field" } = constraints;

  // Normalize: trim whitespace
  const trimmed = (input ?? "").trim();

  // Required check
  if (required && trimmed.length === 0) {
    return invalid(trimmed, message ?? `${label} is required`);
  }

  // Skip further validation if empty and not required
  if (trimmed.length === 0) {
    return valid(trimmed);
  }

  // Min length check (like Pydantic's min_length)
  if (min !== undefined && trimmed.length < min) {
    return invalid(
      trimmed,
      message ?? `${label} must be at least ${min} character${min === 1 ? "" : "s"}`
    );
  }

  // Max length check (like Pydantic's max_length)
  if (max !== undefined && trimmed.length > max) {
    return invalid(
      trimmed,
      message ?? `${label} must be at most ${max} characters`
    );
  }

  // Pattern check (like Pydantic's pattern)
  if (pattern && !pattern.test(trimmed)) {
    return invalid(trimmed, message ?? `${label} format is invalid`);
  }

  return valid(trimmed);
}

// ============================================================================
// Number Validators
// ============================================================================

/**
 * Normalizes and validates a numeric field.
 * Handles string input parsing and constraint validation.
 */
export function validateNumber(
  input: number | string | null | undefined,
  constraints: FieldConstraints = {}
): ValidationResult<number | null> {
  const { min, max, required = false, message, label = "Value" } = constraints;

  // Normalize: parse string input
  let value: number | null = null;

  if (input === null || input === undefined || input === "") {
    value = null;
  } else if (typeof input === "number") {
    value = isNaN(input) ? null : input;
  } else if (typeof input === "string") {
    const trimmed = input.trim();
    if (trimmed === "") {
      value = null;
    } else {
      const parsed = parseFloat(trimmed);
      value = isNaN(parsed) ? null : parsed;
    }
  }

  // Required check
  if (required && value === null) {
    return invalid(value, message ?? `${label} is required`);
  }

  // Skip further validation if null and not required
  if (value === null) {
    return valid(value);
  }

  // Min value check (like Pydantic's ge)
  if (min !== undefined && value < min) {
    return invalid(
      value,
      message ?? `${label} must be at least ${min}`
    );
  }

  // Max value check (like Pydantic's le)
  if (max !== undefined && value > max) {
    return invalid(
      value,
      message ?? `${label} must be at most ${max}`
    );
  }

  return valid(value);
}

/**
 * Validates an integer (whole number) field.
 */
export function validateInteger(
  input: number | string | null | undefined,
  constraints: FieldConstraints = {}
): ValidationResult<number | null> {
  const result = validateNumber(input, constraints);

  if (!result.isValid || result.value === null) {
    return result;
  }

  // Check if it's a whole number
  if (!Number.isInteger(result.value)) {
    return invalid(
      result.value,
      constraints.message ?? `${constraints.label ?? "Value"} must be a whole number`
    );
  }

  return result;
}

// ============================================================================
// Composite Validators
// ============================================================================

/**
 * Chains multiple validators together.
 * Stops at the first validation error.
 */
export function chain<T>(...validators: Validator<T, T>[]): Validator<T, T> {
  return (input: T) => {
    let current = input;

    for (const validator of validators) {
      const result = validator(current);
      if (!result.isValid) {
        return result;
      }
      current = result.value;
    }

    return valid(current);
  };
}

/**
 * Makes a validator optional - skips validation if value is empty/null.
 */
export function optional<TInput, TOutput>(
  validator: Validator<TInput, TOutput>
): Validator<TInput | null | undefined, TOutput | null> {
  return (input) => {
    if (input === null || input === undefined) {
      return valid(null);
    }
    if (typeof input === "string" && input.trim() === "") {
      return valid(null);
    }
    return validator(input) as ValidationResult<TOutput | null>;
  };
}

// ============================================================================
// Form-Level Validation
// ============================================================================

/**
 * Schema definition for form validation.
 * Maps field names to their validators.
 */
export type ValidationSchema<T> = {
  [K in keyof T]?: Validator<unknown, T[K]>;
};

/**
 * Result of validating an entire form.
 */
export interface FormValidationResult<T> {
  /** The normalized form values */
  values: T;
  /** Whether all fields are valid */
  isValid: boolean;
  /** Map of field names to error messages */
  errors: Partial<Record<keyof T, string>>;
  /** List of all error messages */
  errorList: string[];
}

/**
 * Validates an entire form against a schema.
 * Returns normalized values and all validation errors.
 */
export function validateForm<T extends Record<string, unknown>>(
  data: Partial<T>,
  schema: ValidationSchema<T>
): FormValidationResult<T> {
  const values = { ...data } as T;
  const errors: Partial<Record<keyof T, string>> = {};
  const errorList: string[] = [];
  let isValid = true;

  for (const key of Object.keys(schema) as (keyof T)[]) {
    const validator = schema[key];
    if (!validator) continue;

    const result = validator(data[key]);
    values[key] = result.value;

    if (!result.isValid && result.error) {
      errors[key] = result.error;
      errorList.push(result.error);
      isValid = false;
    }
  }

  return { values, isValid, errors, errorList };
}

// ============================================================================
// Field-Specific Validators (Matching Backend DTOs)
// ============================================================================

/**
 * Validates a recipe name (required, min 1 char, max 255 chars).
 * Mirrors RecipeBaseDTO.recipe_name
 */
export function validateRecipeName(input: string | null | undefined): ValidationResult<string> {
  return validateString(input, {
    required: true,
    min: 1,
    max: 255,
    label: "Recipe name",
  });
}

/**
 * Validates an ingredient name (required, min 1 char, max 255 chars).
 * Mirrors IngredientBaseDTO.name / ShoppingItemBaseDTO.ingredient_name
 */
export function validateIngredientName(input: string | null | undefined): ValidationResult<string> {
  return validateString(input, {
    required: true,
    min: 1,
    max: 255,
    label: "Ingredient name",
  });
}

/**
 * Validates a quantity (optional, must be >= 0).
 * Mirrors RecipeIngredientDTO.quantity / ShoppingItemBaseDTO.quantity
 */
export function validateQuantity(input: number | string | null | undefined): ValidationResult<number | null> {
  return validateNumber(input, {
    min: 0,
    label: "Quantity",
  });
}

/**
 * Validates servings (optional, must be >= 1).
 * Mirrors RecipeBaseDTO.servings
 */
export function validateServings(input: number | string | null | undefined): ValidationResult<number | null> {
  return validateInteger(input, {
    min: 1,
    label: "Servings",
  });
}

/**
 * Validates total time in minutes (optional, must be >= 0).
 * Mirrors RecipeBaseDTO.total_time
 */
export function validateTotalTime(input: number | string | null | undefined): ValidationResult<number | null> {
  return validateInteger(input, {
    min: 0,
    label: "Total time",
  });
}

/**
 * Validates a unit string (optional, max 50 chars).
 * Mirrors ShoppingItemBaseDTO.unit
 */
export function validateUnit(input: string | null | undefined): ValidationResult<string> {
  return validateString(input, {
    max: 50,
    label: "Unit",
  });
}

/**
 * Validates a category string (optional, max 100 chars).
 * Mirrors ShoppingItemBaseDTO.category
 */
export function validateCategory(input: string | null | undefined): ValidationResult<string> {
  return validateString(input, {
    max: 100,
    label: "Category",
  });
}

/**
 * Validates pagination limit (1-100).
 * Mirrors RecipeFilterDTO.limit
 */
export function validateLimit(input: number | string | null | undefined): ValidationResult<number | null> {
  return validateInteger(input, {
    min: 1,
    max: 100,
    label: "Limit",
  });
}

/**
 * Validates pagination offset (>= 0).
 * Mirrors RecipeFilterDTO.offset
 */
export function validateOffset(input: number | string | null | undefined): ValidationResult<number | null> {
  return validateInteger(input, {
    min: 0,
    label: "Offset",
  });
}

/**
 * Validates sort order (asc or desc).
 * Mirrors RecipeFilterDTO.sort_order
 */
export function validateSortOrder(input: string | null | undefined): ValidationResult<string> {
  return validateString(input, {
    pattern: /^(asc|desc)$/,
    label: "Sort order",
    message: "Sort order must be 'asc' or 'desc'",
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Creates a debounced validator for async validation (e.g., checking duplicates).
 */
export function createAsyncValidator<T>(
  checkFn: (value: T) => Promise<string | null>,
  debounceMs: number = 300
): (value: T, callback: (error: string | null) => void) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (value: T, callback: (error: string | null) => void) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(async () => {
      const error = await checkFn(value);
      callback(error);
    }, debounceMs);
  };
}

/**
 * Collects errors from multiple validation results (for bulk operations).
 * Mirrors backend's BulkOperationResultDTO pattern.
 */
export function collectErrors<T>(
  items: T[],
  validate: (item: T, index: number) => ValidationResult<unknown>
): { valid: T[]; errors: Array<{ index: number; item: T; error: string }> } {
  const valid: T[] = [];
  const errors: Array<{ index: number; item: T; error: string }> = [];

  items.forEach((item, index) => {
    const result = validate(item, index);
    if (result.isValid) {
      valid.push(item);
    } else if (result.error) {
      errors.push({ index, item, error: result.error });
    }
  });

  return { valid, errors };
}

// ============================================================================
// Unit Categorization (Matches backend app/utils/unit_conversion.py)
// ============================================================================

/** Mass units that require a quantity value, including spellings the list knows how to add. */
export const MASS_UNITS = new Set([
  "oz", "ounce", "ounces",
  "lb", "lbs", "pound", "pounds", "pound(s)",
  "g", "gram", "grams",
  "kg", "kilogram", "kilograms",
]);

/** Volume units that require a quantity value, including spellings the list knows how to add. */
export const VOLUME_UNITS = new Set([
  "tsp", "t", "teaspoon", "teaspoons",
  "tbs", "tbsp", "tablespoon", "tablespoons",
  "cup", "cups",
  "ml", "milliliter", "milliliters", "millilitre", "millilitres",
  "l", "liter", "liters", "litre", "litres",
  "fl oz", "floz", "fluid ounce", "fluid ounces",
]);

/** Count units where quantity is optional */
export const COUNT_UNITS = new Set([
  "", "stick", "bag", "box", "can", "jar", "package",
  "piece", "slice", "whole", "pinch", "dash", "to-taste"
]);

/**
 * Check if a unit requires a quantity value.
 * Mass and volume units always require quantity.
 * Count units (and unknown units) do not require quantity.
 */
export function unitRequiresQuantity(unit: string | null | undefined): boolean {
  const raw = (unit ?? "").trim();
  // A capital T is a tablespoon. Lowercasing would make it look like a teaspoon.
  if (raw === "T" || raw === "T.") return true;
  const normalized = raw
    .toLowerCase()
    .replace(/\./g, " ")
    .replace(/-/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return MASS_UNITS.has(normalized) || VOLUME_UNITS.has(normalized);
}

/**
 * Field-level errors for an ingredient row.
 */
export interface IngredientFieldErrors {
  name?: string;
  quantity?: string;
}

/**
 * Validates an ingredient row with unit-aware quantity validation.
 * - Name is always required (1-255 chars)
 * - Quantity is required only for mass/volume units
 * - Quantity must be >= 0 when provided
 */
export function validateIngredientRow(
  name: string | null | undefined,
  quantity: number | null | undefined,
  unit: string | null | undefined
): { isValid: boolean; errors: IngredientFieldErrors } {
  const errors: IngredientFieldErrors = {};

  // Validate name (required, 1-255 chars)
  const trimmedName = (name ?? "").trim();
  if (trimmedName.length === 0) {
    errors.name = "Ingredient name is required";
  } else if (trimmedName.length > 255) {
    errors.name = "Name must be at most 255 characters";
  }

  // Validate quantity based on unit type
  if (unitRequiresQuantity(unit)) {
    if (quantity === null || quantity === undefined) {
      errors.quantity = "Quantity required for this unit";
    } else if (quantity < 0) {
      errors.quantity = "Quantity must be at least 0";
    }
  } else if (quantity !== null && quantity !== undefined && quantity < 0) {
    // For count units, quantity is optional but must be >= 0 if provided
    errors.quantity = "Quantity must be at least 0";
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}
