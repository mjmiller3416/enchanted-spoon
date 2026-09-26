"use client";

import * as React from "react";
import { Check, Plus } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverAnchor,
} from "@/components/ui/popover";
import { ingredientApi } from "@/lib/api";
import {
  useIngredientAutocomplete,
  type AutocompleteIngredient,
} from "@/hooks/forms/useIngredientAutocomplete";

export type { AutocompleteIngredient } from "@/hooks/forms/useIngredientAutocomplete";

export interface IngredientAutocompleteProps {
  id?: string;
  "aria-label"?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  /** Available ingredients to search/filter. When omitted, fetches automatically. */
  ingredients?: AutocompleteIngredient[];
  /** Current input value (controlled) */
  value: string;
  /** Called when input value changes */
  onValueChange: (value: string) => void;
  /** Called when an existing ingredient is selected (recipe form use case) */
  onIngredientSelect?: (ingredient: AutocompleteIngredient) => void;
  /** Called when user submits a new ingredient name (not in list) */
  onNewIngredient?: (name: string) => void;
  /** Called when a category is determined from selection (shopping use case) */
  onCategoryChange?: (category: string) => void;
  /** Called when user presses Enter with valid input and dropdown is closed */
  onSubmit?: () => void;
  /** Placeholder text */
  placeholder?: string;
  /** Additional class names */
  className?: string;
  /** Whether the input is disabled */
  disabled?: boolean;
  /** Auto-focus the input on mount */
  autoFocus?: boolean;
}

export function IngredientAutocomplete({
  id,
  "aria-label": ariaLabel = "Ingredient name",
  "aria-describedby": ariaDescribedBy,
  "aria-invalid": ariaInvalid,
  ingredients: ingredientsProp,
  value,
  onValueChange,
  onIngredientSelect,
  onNewIngredient,
  onCategoryChange,
  onSubmit,
  placeholder = "Type ingredient name...",
  className,
  disabled = false,
  autoFocus = false,
}: IngredientAutocompleteProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listId = React.useId();
  const listRef = React.useRef<HTMLDivElement>(null);

  // Self-fetch ingredients when none are provided via props
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [fetchedIngredients, setFetchedIngredients] = React.useState<AutocompleteIngredient[]>([]);
  const shouldFetch = ingredientsProp === undefined;

  React.useEffect(() => {
    if (!shouldFetch || !isLoaded || !isSignedIn) return;

    const fetchIngredients = async () => {
      try {
        const token = await getToken();
        const ingredients = await ingredientApi.list(undefined, token);
        const transformed: AutocompleteIngredient[] = ingredients.map((ing) => ({
          id: ing.id,
          name: ing.ingredient_name,
          category: ing.ingredient_category,
        }));
        setFetchedIngredients(transformed);
      } catch (error) {
        console.error("Failed to fetch ingredients:", error);
      }
    };
    fetchIngredients();
  }, [shouldFetch, isLoaded, isSignedIn, getToken]);

  const ingredients = ingredientsProp ?? fetchedIngredients;

  // Internal selection handler that delegates to the appropriate callback
  const handleIngredientSelectInternal = React.useCallback(
    (ingredient: AutocompleteIngredient) => {
      if (onIngredientSelect) {
        onIngredientSelect(ingredient);
      } else {
        // Shopping use case: update name and category directly
        onValueChange(ingredient.name);
      }
      if (ingredient.category && onCategoryChange) {
        onCategoryChange(ingredient.category);
      }
    },
    [onIngredientSelect, onValueChange, onCategoryChange]
  );

  const {
    open,
    setOpen,
    highlightedIndex,
    setHighlightedIndex,
    exactMatch,
    items,
    handleSelect,
    handleInputChange,
    handleKeyDown: hookKeyDown,
    handleFocus,
    handleBlur,
  } = useIngredientAutocomplete({
    ingredients,
    value,
    onValueChange,
    onIngredientSelect: handleIngredientSelectInternal,
    onNewIngredient,
  });

  // Wrap keydown to support onSubmit when dropdown is closed
  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (open && items.length > 0) {
        hookKeyDown(e);
        return;
      }
      if (e.key === "Enter" && value.trim() && onSubmit) {
        e.preventDefault();
        onSubmit();
        return;
      }
      hookKeyDown(e);
    },
    [open, items.length, hookKeyDown, value, onSubmit]
  );

  // Scroll highlighted item into view
  React.useEffect(() => {
    if (open && listRef.current) {
      const highlighted = listRef.current.children[highlightedIndex] as HTMLElement;
      highlighted?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightedIndex, open]);

  return (
    <div className="relative flex-1 min-w-0">
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverAnchor asChild>
        <Input
          ref={inputRef}
          id={id}
          role="combobox"
          aria-label={ariaLabel}
          aria-describedby={ariaDescribedBy}
          aria-invalid={ariaInvalid}
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          aria-activedescendant={open && items[highlightedIndex] ? `${listId}-${highlightedIndex}` : undefined}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={() => handleBlur(listRef)}
          placeholder={placeholder}
          disabled={disabled}
          autoFocus={autoFocus}
          autoComplete="off"
          className={cn("w-full", className)}
        />
      </PopoverAnchor>

      <PopoverContent
        className="w-[--radix-popover-trigger-width] p-0"
        align="start"
        side="bottom"
        sideOffset={4}
        onOpenAutoFocus={(e) => e.preventDefault()}
        onInteractOutside={(e) => {
          if (e.target === inputRef.current) {
            e.preventDefault();
          }
        }}
      >
        <div
          ref={listRef}
          id={listId}
          className="max-h-52 overflow-y-auto p-1"
          role="listbox"
        >
          {items.length === 0 && (
            <div className="py-3 text-center text-sm text-muted-foreground">
              No ingredients found.
            </div>
          )}

          {items.map((item, index) => (
            <div
              key={item.type === "ingredient" ? item.data?.id : "create-new"}
              role="option"
              id={`${listId}-${index}`}
              aria-selected={highlightedIndex === index}
              className={cn(
                "flex items-center justify-between rounded-sm px-2 py-1.5 text-sm cursor-pointer transition-colors duration-150",
                highlightedIndex === index
                  ? "bg-accent text-accent-foreground"
                  : "hover:bg-accent/50"
              )}
              onClick={() => handleSelect(index)}
              onMouseEnter={() => setHighlightedIndex(index)}
            >
              {item.type === "ingredient" && item.data ? (
                <>
                  <div className="flex flex-col gap-1">
                    <span className="font-medium">{item.data.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {item.data.category}
                    </span>
                  </div>
                  {exactMatch?.id === item.data.id && (
                    <Check className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </>
              ) : item.type === "create" && item.name ? (
                <div className="flex items-center gap-2">
                  <Plus className="h-4 w-4 shrink-0 text-primary" />
                  <span>
                    Create <span className="font-medium text-primary">&quot;{item.name}&quot;</span>
                  </span>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </PopoverContent>
    </Popover>
    </div>
  );
}
