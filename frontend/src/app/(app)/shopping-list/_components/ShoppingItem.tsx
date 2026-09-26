"use client";

import { Flag, Loader2 } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn, formatQuantity } from "@/lib/utils";
import type { ShoppingItemResponseDTO } from "@/types/shopping";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface ShoppingItemProps {
  item: ShoppingItemResponseDTO;
  pending?: boolean;
  onToggle: (id: number) => void;
  onToggleFlagged: (id: number) => void;
}

/**
 * ShoppingItem - Individual shopping list item with checkbox
 *
 * Features:
 * - Click anywhere on the row to toggle
 * - Checked items show strikethrough + faded appearance
 * - Recipe source display ("from Recipe Name" or "from Multiple recipes")
 * - Tooltip shows recipe sources with usage counts (e.g., "Air Fryer Potatoes (×2)")
 * - Quantity badge on the right
 */
export function ShoppingItem({ item, pending = false, onToggle, onToggleFlagged }: ShoppingItemProps) {
  const handleClick = () => {
    if (!pending) onToggle(item.id);
  };

  const handleFlagClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!pending) onToggleFlagged(item.id);
  };

  // Format quantity with unit for badge display
  const quantityBadge = item.unit
    ? `${formatQuantity(item.quantity)} ${item.unit}`
    : formatQuantity(item.quantity);

  // Format recipe source display
  const getRecipeSourceText = () => {
    if (item.source === "manual") {
      return "added manually";
    }
    if (item.source !== "recipe") {
      // External app source slug, e.g. "tada" -> "from Tada"
      return `from ${item.source.charAt(0).toUpperCase()}${item.source.slice(1)}`;
    }
    if (!item.recipe_sources || item.recipe_sources.length === 0) {
      return "from recipe";
    }
    if (item.recipe_sources.length === 1) {
      const source = item.recipe_sources[0];
      // Show count if > 1, e.g., "from Air Fryer Potatoes (×2)"
      const countSuffix = source.count > 1 ? ` (×${source.count})` : "";
      return `from ${source.recipe_name}${countSuffix}`;
    }
    return "from Multiple recipes";
  };

  // Check if item has multiple recipe sources (for tooltip)
  const hasMultipleRecipes =
    item.source === "recipe" &&
    item.recipe_sources &&
    item.recipe_sources.length > 1;

  return (
    <div
      aria-busy={pending}
      onClick={handleClick}
      className={cn(
        "group flex items-center gap-3 px-3 py-3 rounded-lg cursor-pointer",
        "transition-all duration-150 ease-out",
        item.have
          ? "opacity-60 hover:bg-hover/30"
          : "hover:bg-hover/50 hover:translate-x-1"
      )}
    >
      {/* Checkbox */}
      <Checkbox
        aria-label={`Collected ${item.ingredient_name}`}
        disabled={pending}
        checked={item.have}
        onCheckedChange={() => onToggle(item.id)}
        onClick={(e) => e.stopPropagation()}
        className={cn(
          item.have && "data-[state=checked]:bg-success data-[state=checked]:border-success"
        )}
      />

      {/* Quantity badge */}
      <Badge
        variant={item.have ? "muted" : "outline"}
        className={cn(
          "whitespace-nowrap",
          !item.have && "bg-primary/20 text-primary border-transparent"
        )}
      >
        {quantityBadge}
      </Badge>

      {/* Item content */}
      <div className="flex-1 min-w-0">
        {/* Ingredient name */}
        <span
          className={cn(
            "text-foreground font-medium block break-words transition-all duration-200",
            item.have && "line-through text-muted-foreground decoration-muted/50"
          )}
        >
          {item.ingredient_name}
        </span>

        {/* Recipe source - with tooltip for multiple recipes */}
        {hasMultipleRecipes && !item.have ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                onClick={(e) => e.stopPropagation()}
                className={cn(
                  "text-xs text-muted-foreground transition-all duration-200",
                  "cursor-help underline decoration-dotted decoration-muted/50",
                  "inline-block" // Shrink to text width only
                )}
              >
                {getRecipeSourceText()}
              </span>
            </TooltipTrigger>
            <TooltipContent side="bottom" align="start" className="max-w-xs">
              <p className="font-medium mb-1">Used in:</p>
              <ul className="space-y-0.5">
                {item.recipe_sources.map((source) => (
                  <li key={source.recipe_name} className="text-muted-foreground">
                    • {source.recipe_name}{source.count > 1 ? ` (×${source.count})` : ""}
                  </li>
                ))}
              </ul>
            </TooltipContent>
          </Tooltip>
        ) : (
          <span
            className={cn(
              "text-xs text-muted-foreground block truncate transition-all duration-200",
              item.have && "text-foreground-disabled"
            )}
          >
            {getRecipeSourceText()}
          </span>
        )}
      </div>

      {/* Flag icon - anchored to right */}
      <Button
        disabled={pending}
        variant="ghost"
        size="icon-sm"
        onClick={handleFlagClick}
        aria-label={item.flagged ? "Remove item flag" : "Flag item"}
        aria-pressed={item.flagged}
        className={cn(
          "shrink-0",
          item.flagged
            ? "text-warning"
            : "text-muted-foreground/40 hover:text-muted-foreground"
        )}
      >
        {pending ? <Loader2 className="size-4 animate-spin" strokeWidth={1.5} /> : <Flag
          strokeWidth={1.5}
          className={cn(
            "size-4",
            item.flagged && "fill-warning"
          )}
        />}
      </Button>
    </div>
  );
}
