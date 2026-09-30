"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuPortal, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem } from "@/components/ui/dropdown-menu";
import { RecipeBannerImage } from "@/components/recipe/RecipeBannerImage";
import { ShoppingCart, Users, Clock, Bookmark, Loader2 } from "lucide-react";
import { formatTime } from "@/lib/quantityUtils";
import { ShoppingMode } from "@/types/shopping";

// ============================================================================
// TYPES
// ============================================================================

export interface MealGridItem {
  id: number;
  name: string;
  imageUrl: string | null;
  bannerImageUrl?: string | null;
  servings?: number | null;
  totalTime?: number | null;
  isSaved?: boolean;
  shoppingMode?: ShoppingMode;
}

interface MealGridCardProps {
  item: MealGridItem;
  isSelected?: boolean;
  isAnyDragging?: boolean;
  onClick?: () => void;
  onSetShoppingMode?: (mode: ShoppingMode) => void;
  isShoppingModePending?: boolean;
  className?: string;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/** Get tooltip text explaining the current shopping mode */
function getShoppingModeTooltip(mode: ShoppingMode): string {
  switch (mode) {
    case "all":
      return "All ingredients added to shopping list";
    case "produce_only":
      return "Only produce added to shopping list";
    case "none":
      return "Excluded from shopping list";
  }
}

// ============================================================================
// MEAL GRID CARD COMPONENT
// ============================================================================

/**
 * Individual meal card for the grid display.
 * Shows recipe image, name, servings, time, and status indicators.
 */
export function MealGridCard({
  item,
  isSelected = false,
  isAnyDragging = false,
  onClick,
  onSetShoppingMode,
  isShoppingModePending = false,
  className,
}: MealGridCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.id });

  // When dragging: hide the original card (DragOverlay renders the floating copy).
  // For non-dragged items: only apply transition while a drag is active so items
  // smoothly shift to make room. When the drag ends, transitions are disabled
  // so all cards snap instantly to their final positions (no flash).
  const style = isDragging
    ? undefined
    : {
        transform: CSS.Translate.toString(transform),
      transition: isAnyDragging ? transition : 'none',
      };

  const shoppingMode = item.shoppingMode ?? "all";

  // Keyboard: Enter opens the meal; Space (via the sensor's keyboardCodes)
  // lifts it for reordering. While a keyboard drag is active the sensor owns
  // all key handling at the document level, so we stay out of the way.
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isDragging || e.target !== e.currentTarget) return;
    if (e.key === "Enter") {
      e.preventDefault();
      onClick?.();
      return;
    }
    (listeners?.onKeyDown as ((e: React.KeyboardEvent) => void) | undefined)?.(e);
  };

  return (
    <Card
      ref={setNodeRef}
      style={style}
      onClick={onClick}
      aria-label={`${item.name} — Enter or click to view, Space or hold to reorder`}
      className={cn(
        // Base styles
        // touch-pan-y (not touch-none) so native vertical scroll still works when a
        // swipe starts over a card — the TouchSensor's press-and-hold delay (see
        // MealGrid.tsx) distinguishes an intentional drag from a scroll, while the
        // MouseSensor uses a small distance threshold so desktop drags start instantly.
        "group cursor-pointer overflow-hidden touch-pan-y",
        "pb-0 pt-0 gap-0",
        // Liftable hover effect (disabled while dragging to prevent transform conflicts)
        !isDragging && "liftable hover:bg-hover",
        // Focus styles
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        // Selected state - use outline instead of ring so it persists on hover (ring uses box-shadow which gets overridden by liftable)
        isSelected && "outline outline-2 outline-primary",
        // Dragging state - hidden (space preserved) so DragOverlay can render the floating copy
        isDragging && "opacity-0 transition-none",
        className
      )}
      {...attributes}
      {...listeners}
      onKeyDown={handleKeyDown}
    >
      {/* Image Section */}
      <div className="relative w-full overflow-hidden">
        <RecipeBannerImage
          bannerSrc={item.bannerImageUrl}
          fallbackSrc={item.imageUrl}
          alt={item.name}
          aspectRatio="16/9"
          className={cn(
            // Hover zoom effect (disabled while dragging to prevent jitter)
            !isDragging && "transition-transform duration-300 group-hover:scale-105"
          )}
        />

        {/* Status Icons - Top Right */}
        <div className="absolute top-2 right-2 flex gap-1">
          {/* Portaled out of the card: the card's hover lift (transform) would otherwise become
              the menu's containing block and make it jump as hover toggles. modal={false}
              skips Radix's scroll lock, which is what caused layout shift with portals. */}
          <DropdownMenu modal={false}>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon-sm" disabled={isShoppingModePending} aria-label={`Shopping mode: ${getShoppingModeTooltip(shoppingMode)}`} onPointerDown={event => event.stopPropagation()} onKeyDown={event => event.stopPropagation()} onClick={event => event.stopPropagation()}>
                {isShoppingModePending ? <Loader2 className="size-4 animate-spin" strokeWidth={1.5} /> : <ShoppingCart className="size-4" strokeWidth={1.5} />}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuPortal>
              <DropdownMenuContent onPointerDown={event => event.stopPropagation()} onClick={event => event.stopPropagation()} onKeyDown={event => event.stopPropagation()}>
                <DropdownMenuRadioGroup value={shoppingMode} onValueChange={value => onSetShoppingMode?.(value as ShoppingMode)}>
                  <DropdownMenuRadioItem value="all">All ingredients</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="produce_only">Produce only</DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="none">Exclude from shopping</DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenuPortal>
          </DropdownMenu>

          {/* Saved Indicator */}
          {item.isSaved && (
            <div className="size-6 rounded-full bg-overlay-strong flex items-center justify-center">
              <Bookmark
                className="size-3.5 text-primary fill-current"
                strokeWidth={1.5}
              />
            </div>
          )}
        </div>
      </div>

      {/* Content Section */}
      <div className="p-3">
        <h3 className="text-sm font-semibold text-foreground truncate mb-1 group-hover:text-primary transition-colors">
          {item.name}
        </h3>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {item.servings != null && (
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" strokeWidth={1.5} />
              {item.servings} servings
            </span>
          )}
          {item.totalTime != null && (
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" strokeWidth={1.5} />
              {formatTime(item.totalTime)}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}

// ============================================================================
// DRAG OVERLAY COMPONENT (presentational — no useSortable hook)
// ============================================================================

/**
 * Presentational clone of MealGridCard rendered inside DragOverlay.
 * Renders outside the grid flow so it doesn't interfere with layout.
 */
export function MealGridCardOverlay({ item }: { item: MealGridItem }) {
  const shoppingMode = item.shoppingMode ?? "all";

  return (
    <Card
      className={cn(
        "cursor-grabbing overflow-hidden",
        "pb-0 pt-0 gap-0",
        "shadow-lg scale-105 rotate-1"
      )}
    >
      {/* Image Section */}
      <div className="relative w-full overflow-hidden">
        <RecipeBannerImage
          bannerSrc={item.bannerImageUrl}
          fallbackSrc={item.imageUrl}
          alt={item.name}
          aspectRatio="16/9"
        />

        {/* Status Icons - Top Right */}
        <div className="absolute top-2 right-2 flex gap-1">
          <div className="size-6 rounded-full bg-overlay-strong flex items-center justify-center">
            <ShoppingCart
              className={cn(
                "size-3.5",
                shoppingMode === "none" && "text-destructive",
                shoppingMode === "produce_only" && "text-warning",
                shoppingMode === "all" && "text-secondary"
              )}
              strokeWidth={1.5}
            />
          </div>

          {item.isSaved && (
            <div className="size-6 rounded-full bg-overlay-strong flex items-center justify-center">
              <Bookmark
                className="size-3.5 text-primary fill-current"
                strokeWidth={1.5}
              />
            </div>
          )}
        </div>
      </div>

      {/* Content Section */}
      <div className="p-3">
        <h3 className="text-sm font-semibold text-foreground truncate mb-1">
          {item.name}
        </h3>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {item.servings != null && (
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" strokeWidth={1.5} />
              {item.servings} servings
            </span>
          )}
          {item.totalTime != null && (
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" strokeWidth={1.5} />
              {formatTime(item.totalTime)}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}
