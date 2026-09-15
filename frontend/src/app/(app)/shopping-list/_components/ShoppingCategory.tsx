"use client";

import { useState } from "react";
import { ShoppingItem } from "./ShoppingItem";
import type { ShoppingItemResponseDTO } from "@/types/shopping";
import { cn } from "@/lib/utils";
import { ChevronUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RecipeIcon, type RecipeIconData } from "@/components/common/RecipeIcon";

// Storage key prefix for persisting collapsed state
const COLLAPSED_STORAGE_KEY = "shopping-category-collapsed";

// ============================================================================
// CATEGORY ICON MAPPING
// ============================================================================

/**
 * Maps ingredient category values to icons.
 * Uses lowercase keys to match against normalized category values.
 */
const CATEGORY_ICONS: Record<string, RecipeIconData> = {
  produce: { type: "icon", value: "broccoli" },
  dairy: { type: "icon", value: "cheese" },
  deli: { type: "icon", value: "salami" },
  meat: { type: "icon", value: "cuts-of-beef" },
  condiments: { type: "icon", value: "sauce-bottle" },
  "oils-and-vinegars": { type: "icon", value: "olive-oil" },
  seafood: { type: "icon", value: "prawn" },
  pantry: { type: "icon", value: "tin-can" },
  spices: { type: "icon", value: "spice" },
  frozen: { type: "icon", value: "ice" },
  bakery: { type: "icon", value: "baguette" },
  baking: { type: "icon", value: "flour" },
  beverages: { type: "icon", value: "cola" },
  other: { type: "icon", value: "grocery-bag" },
};

const DEFAULT_CATEGORY_ICON: RecipeIconData = { type: "icon", value: "grocery-bag" };

function getCategoryIcon(category: string): RecipeIconData {
  // Normalize to lowercase for matching
  const normalizedCategory = category.toLowerCase();
  return CATEGORY_ICONS[normalizedCategory] || DEFAULT_CATEGORY_ICON;
}

// ============================================================================
// COMPONENT
// ============================================================================

interface ShoppingCategoryProps {
  category: string;
  items: ShoppingItemResponseDTO[];
  pendingIds?: Set<number>;
  onToggleItem: (id: number) => void;
  onToggleFlagged: (id: number) => void;
}

/**
 * ShoppingCategory - Displays a category section with items
 *
 * Features:
 * - Collapsible card with icon and progress bar
 * - Items sorted alphabetically
 * - Unchecked items at top, checked items at bottom
 */
export function ShoppingCategory({
  category,
  items,
  pendingIds,
  onToggleItem,
  onToggleFlagged,
}: ShoppingCategoryProps) {
  // Storage key for this specific category
  const storageKey = `${COLLAPSED_STORAGE_KEY}-${category}`;

  // Calculate if category is complete (needed for initial state)
  const isInitiallyComplete =
    items.length > 0 && items.every((item) => item.have);

  // Initialize expanded state from localStorage, but always expand incomplete categories
  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window === "undefined") return true;

    // If category has unchecked items, always expand (items may have been added)
    if (!isInitiallyComplete) return true;

    // Only respect collapsed localStorage for complete categories
    const stored = localStorage.getItem(storageKey);
    return stored === null ? true : stored !== "collapsed";
  });

  // Track previous complete state to detect when category becomes complete
  const [wasComplete, setWasComplete] = useState(false);

  // Sort items: flagged first, then unchecked, then alphabetically
  const sortedItems = [...items].sort((a, b) => {
    // First sort by flagged status (flagged first)
    if (a.flagged !== b.flagged) {
      return a.flagged ? -1 : 1;
    }
    // Then sort by checked status (unchecked first)
    if (a.have !== b.have) {
      return a.have ? 1 : -1;
    }
    // Then sort alphabetically
    return a.ingredient_name.localeCompare(b.ingredient_name);
  });

  // Calculate progress
  const totalItems = items.length;
  const checkedCount = items.filter((item) => item.have).length;
  const progress = totalItems > 0 ? (checkedCount / totalItems) * 100 : 0;
  const isComplete = totalItems > 0 && checkedCount === totalItems;

  // Auto-collapse when category becomes complete, auto-expand when items are added
  if (isComplete && !wasComplete) {
    setWasComplete(true);
    setIsExpanded(false);
    localStorage.setItem(storageKey, "collapsed");
  } else if (!isComplete && wasComplete) {
    setWasComplete(false);
    setIsExpanded(true);
    localStorage.setItem(storageKey, "expanded");
  }

  // Persist expanded state changes to localStorage
  const handleToggleExpanded = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    localStorage.setItem(storageKey, newExpanded ? "expanded" : "collapsed");
  };

  // Get category icon
  const icon = getCategoryIcon(category);

  return (
    <Card
      className={cn(
        "overflow-hidden p-0",
        isComplete && "bg-success/5 border-success/40"
      )}
    >
      {/* Category header */}
      <Button
        variant="ghost"
        aria-expanded={isExpanded}
        onClick={handleToggleExpanded}
        className="w-full flex items-center gap-3 px-4 py-4 h-auto justify-start rounded-none"
      >
        {/* Category icon */}
        <RecipeIcon icon={icon} className="size-8 flex-shrink-0" />

        {/* Category name and count */}
        <div className="flex-1 text-left">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-semibold text-foreground capitalize">
              {category || "other"}
            </h2>
            {isComplete && (
              <Badge variant="success" size="sm" className="text-success font-semibold" >
                Complete
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground font-normal">
            {checkedCount} of {totalItems} items
          </p>
        </div>

        {/* Progress bar */}
        <div className="w-20 sm:w-24 h-1 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-success transition-all duration-300 ease-out rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Chevron */}
        <ChevronUp
          className={cn(
            "size-5 text-muted-foreground transition-transform duration-200",
            !isExpanded && "rotate-180"
          )}
        />
      </Button>

      {/* Items list */}
      {isExpanded && (
        <div className="px-2 pb-2">
          {sortedItems.map((item) => (
            <ShoppingItem
              key={item.id}
              item={item}
              pending={pendingIds?.has(item.id)}
              onToggle={onToggleItem}
              onToggleFlagged={onToggleFlagged}
            />
          ))}
        </div>
      )}
    </Card>
  );
}
