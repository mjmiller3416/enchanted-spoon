"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { UtensilsCrossed, ArrowRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  usePlannerEntries,
  useMarkComplete,
  useReorderEntries,
  useRefreshPlannerEntries,
  PLANNER_EVENTS,
} from "@/hooks/api";
import { MealQueueItem } from "./MealQueueItem";
import type { PlannerEntryResponseDTO } from "@/types/planner";
import { cn } from "@/lib/utils";
import {
  DndContext,
  closestCenter,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { useSortableDnd } from "@/hooks/ui";

interface MealQueueWidgetProps {
  entries?: PlannerEntryResponseDTO[];
}

export function MealQueueWidget({ entries: initialEntries }: MealQueueWidgetProps) {
  // Use React Query for fetching entries (only if no initialEntries provided)
  const { data: fetchedEntries, isLoading: queryLoading } = usePlannerEntries();
  const markComplete = useMarkComplete();
  const reorderEntries = useReorderEntries();
  const refreshEntries = useRefreshPlannerEntries();

  // Determine which entries to use and derive active entries
  const entries = initialEntries ?? fetchedEntries;
  const activeEntries = useMemo(() => {
    return [...(entries ?? [])]
      .sort((a, b) => a.position - b.position)
      .filter((e) => !e.is_completed);
  }, [entries]);

  const isLoading = !initialEntries && queryLoading;

  const [completingId, setCompletingId] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Drag and drop setup
  const { sensors, modifiers } = useSortableDnd();

  // Listen for planner updates from other components
  useEffect(() => {
    const handlePlannerUpdate = () => refreshEntries();
    window.addEventListener(PLANNER_EVENTS.UPDATED, handlePlannerUpdate);
    return () => window.removeEventListener(PLANNER_EVENTS.UPDATED, handlePlannerUpdate);
  }, [refreshEntries]);

  // Handle drag start
  const handleDragStart = useCallback(() => {
    setIsDragging(true);
  }, []);

  // Handle drag end for reordering (only active entries)
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setIsDragging(false);
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = activeEntries.findIndex((e) => e.id === active.id);
      const newIndex = activeEntries.findIndex((e) => e.id === over.id);

      if (oldIndex === -1 || newIndex === -1) return;

      // Calculate reordered IDs for API call (optimistic update handled by mutation)
      const reorderedIds = arrayMove(activeEntries, oldIndex, newIndex).map((e) => e.id);
      reorderEntries.mutate(reorderedIds);
    },
    [activeEntries, reorderEntries]
  );

  // Handle drag cancel
  const handleDragCancel = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Handle marking a meal as cooked
  const handleComplete = useCallback(
    (entryId: number) => {
      setCompletingId(entryId);

      markComplete.mutate(entryId, {
        onSettled: async () => {
          // Wait for fade animation, then clear completing state
          await new Promise((resolve) => setTimeout(resolve, 300));
          setCompletingId(null);
        },
      });
    },
    [markComplete]
  );

  const hasEntries = activeEntries.length > 0;

  return (
    <Card className="flex flex-col h-full px-5 pt-5 pb-3 overflow-hidden shadow-raised">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <UtensilsCrossed className="w-5 h-5 text-secondary" />
          <h2 className="text-lg font-semibold text-foreground">Meal Queue</h2>
        </div>
        <Link
          href="/meal-planner"
          className="flex items-center gap-1 text-sm transition-colors duration-150 text-primary hover:text-primary/80"
        >
          View All
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Meal List */}
      {isLoading ? (
        <div className="flex-1 space-y-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-3 p-3">
              <Skeleton className="w-5 h-5" />
              <Skeleton className="w-12 h-12 rounded-lg" />
              <div className="flex-1 space-y-2">
                <Skeleton className="w-3/4 h-4" />
                <Skeleton className="w-1/3 h-3" />
              </div>
            </div>
          ))}
        </div>
      ) : !hasEntries ? (
        <div className="flex items-center justify-center flex-1 text-center text-muted-foreground">
          <div>
            <p>No meals in queue</p>
            <p className="mt-1 text-sm">Add some meals to get started!</p>
          </div>
        </div>
      ) : (
        <div className={cn(
          "flex-1 min-h-0 overflow-auto p-2 -m-2",
          isDragging && "scrollbar-hidden"
        )}>
          {/* Meals with drag-and-drop */}
          <DndContext
            sensors={sensors}
            modifiers={modifiers}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragCancel={handleDragCancel}
          >
            <SortableContext
              items={activeEntries.map((e) => e.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {activeEntries.map((entry) => (
                  <MealQueueItem
                    key={entry.id}
                    entry={entry}
                    isCompleting={completingId === entry.id}
                    onComplete={handleComplete}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      )}

      {/* Add Meal Footer */}
      <Link href="/meal-planner?create=true" className="block mt-4">
        <Button className="w-full interactive-subtle">
          <Plus className="w-4 h-4 mr-2" />
          Add Meal
        </Button>
      </Link>
    </Card>
  );
}
