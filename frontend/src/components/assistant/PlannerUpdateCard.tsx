"use client";

import { CalendarPlus, Undo2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { PlannerEntryResponseDTO } from "@/types/planner";

interface PlannerUpdateCardProps {
  entries: PlannerEntryResponseDTO[];
  isUndoing: boolean;
  onUndo: () => void;
  onViewPlanner: () => void;
}

/** Confirms meals Genie put on the meal planner, with a jump to the planner and an undo. */
export function PlannerUpdateCard({ entries, isUndoing, onUndo, onViewPlanner }: PlannerUpdateCardProps) {
  const count = entries.length;

  return (
    <Card className="flex-row items-center gap-1 py-1 pl-3 pr-1">
      <CalendarPlus className="size-4 shrink-0 text-primary" strokeWidth={1.5} />
      <span className="px-1 text-sm text-foreground">
        Planned {count} {count === 1 ? "meal" : "meals"}
      </span>
      <Button variant="ghost" size="sm" onClick={onViewPlanner} disabled={isUndoing}>
        View planner
      </Button>
      <Button variant="ghost" size="sm" onClick={onUndo} disabled={isUndoing}>
        {isUndoing ? (
          <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />
        ) : (
          <Undo2 className="size-4" strokeWidth={1.5} />
        )}
        Undo
      </Button>
    </Card>
  );
}
