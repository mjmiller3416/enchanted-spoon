"use client";

import { useState, useEffect } from "react";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
  arrayMove,
} from "@dnd-kit/sortable";
import { Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { MealGridCard, MealGridCardOverlay, MealGridItem } from "./MealGridCard";

// ============================================================================
// TYPES
// ============================================================================

interface MealGridProps {
  items: MealGridItem[];
  selectedId?: number | null;
  onItemClick?: (item: MealGridItem) => void;
  onAddMealClick?: () => void;
  onCycleShoppingMode?: (item: MealGridItem) => void;
  pendingShoppingModeId?: number | null;
  onReorder?: (reorderedItems: MealGridItem[]) => void;
  className?: string;
}

// ============================================================================
// ADD MEAL CARD COMPONENT
// ============================================================================

interface AddMealCardProps {
  onClick?: () => void;
}

function AddMealCard({ onClick }: AddMealCardProps) {
  return (
    <Card
      onClick={onClick}
      tabIndex={0}
      role="button"
      aria-label="Add a new meal"
      className={cn(
        "cursor-pointer overflow-hidden relative",
        "pb-0 pt-0 gap-0",
        "border-dashed border-primary/40 bg-primary/5",
        "hover:border-primary hover:bg-primary/10 transition-all duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      )}
    >
      {/* Invisible spacer matching MealGridCard proportions */}
      <div className="aspect-[16/9]" aria-hidden="true" />
      <div className="p-3" aria-hidden="true">
        <p className="text-sm mb-1 invisible">&nbsp;</p>
        <p className="text-xs invisible">&nbsp;</p>
      </div>
      {/* Centered content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
        <Plus className="size-8 text-muted-foreground" strokeWidth={1.5} />
        <span className="text-sm font-semibold text-muted-foreground">Add Meal</span>
      </div>
    </Card>
  );
}

// ============================================================================
// MEAL GRID COMPONENT
// ============================================================================

/**
 * Grid display of meals with an "Add Meal" placeholder.
 * Responsive: 2 columns on mobile, 3 on tablet, 4 on desktop.
 */
export function MealGrid({
  items: propItems,
  selectedId,
  onItemClick,
  onAddMealClick,
  onCycleShoppingMode,
  pendingShoppingModeId,
  onReorder,
  className,
}: MealGridProps) {
  // Local items state ensures reorder + activeId clear happen in the same render.
  // Without this, the async mutation causes a flash where items are in the old order.
  const [items, setItems] = useState(propItems);
  const [activeId, setActiveId] = useState<number | null>(null);

  // Sync local state when props change (initial load, server updates)
  useEffect(() => {
    setItems(propItems);
  }, [propItems]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { delay: 250, tolerance: 5 },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
      // Space lifts/drops so Enter stays free to open the card (see MealGridCard)
      keyboardCodes: {
        start: ["Space"],
        cancel: ["Escape"],
        end: ["Space", "Enter"],
      },
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over || active.id === over.id) return;

    const oldIndex = items.findIndex((item) => item.id === active.id);
    const newIndex = items.findIndex((item) => item.id === over.id);

    if (oldIndex === -1 || newIndex === -1) return;

    const reorderedItems = arrayMove(items, oldIndex, newIndex);
    setItems(reorderedItems);    // Update local state immediately (same render cycle)
    onReorder?.(reorderedItems); // Notify parent for persistence
  };

  const handleDragCancel = () => {
    setActiveId(null);
  };

  const activeItem = activeId != null ? items.find((i) => i.id === activeId) : null;

  return (
    <div className={className}>
      {/* Grid */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <SortableContext
          items={items.map((item) => item.id)}
          strategy={rectSortingStrategy}
        >
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 auto-rows-fr">
            {items.map((item) => (
              <MealGridCard
                key={item.id}
                item={item}
                isSelected={selectedId === item.id}
                isAnyDragging={activeId != null}
                onClick={() => onItemClick?.(item)}
                onCycleShoppingMode={() => onCycleShoppingMode?.(item)}
                isShoppingModePending={pendingShoppingModeId === item.id}
              />
            ))}

            {/* Add Meal Card - outside SortableContext items, not draggable */}
            <AddMealCard onClick={onAddMealClick} />
          </div>
        </SortableContext>

        {/* Floating drag overlay - rendered outside grid flow */}
        <DragOverlay dropAnimation={null}>
          {activeItem ? <MealGridCardOverlay item={activeItem} /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}
