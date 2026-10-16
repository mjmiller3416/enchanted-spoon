"use client";

import { ShoppingCart, Undo2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { ManualItemsAddResultDTO } from "@/types/shopping";

interface ShoppingUpdateCardProps {
  update: ManualItemsAddResultDTO;
  isUndoing: boolean;
  onUndo: () => void;
  onViewList: () => void;
}

/** Confirms items Genie put on the shopping list, with a jump to the list and an undo. */
export function ShoppingUpdateCard({ update, isUndoing, onUndo, onViewList }: ShoppingUpdateCardProps) {
  const count = update.added.length + update.reactivated.length;

  return (
    <Card className="flex-row items-center gap-1 py-1 pl-3 pr-1">
      <ShoppingCart className="size-4 shrink-0 text-primary" strokeWidth={1.5} />
      <span className="px-1 text-sm text-foreground">
        Added {count} {count === 1 ? "item" : "items"}
      </span>
      <Button variant="ghost" size="sm" onClick={onViewList} disabled={isUndoing}>
        View list
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
