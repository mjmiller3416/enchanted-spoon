"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, ChevronDown, Loader2, NotebookPen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useSaveShoppingNotes, useShoppingNotes } from "@/hooks/api";

const MAX_LENGTH = 5000;
const AUTOSAVE_DELAY_MS = 800;

interface ShoppingNotesProps {
  /** "card" is always open (desktop sidebar); "collapsible" folds behind a header (mobile). */
  variant: "card" | "collapsible";
  className?: string;
}

/**
 * ShoppingNotes - Free-text notes pad for the shopping list
 *
 * Synced to the account (not the device), so notes written on desktop are
 * there on your phone at the store. Autosaves shortly after typing stops and
 * immediately on blur. While you have unsaved edits the local draft wins;
 * otherwise the latest server copy is shown.
 */
export function ShoppingNotes({ variant, className }: ShoppingNotesProps) {
  const { data, isLoading } = useShoppingNotes();
  const { mutate, isPending } = useSaveShoppingNotes();

  // null = no unsaved edits, show the server copy
  const [draft, setDraft] = useState<string | null>(null);
  // null = user hasn't toggled yet; default open when there are notes
  const [open, setOpen] = useState<boolean | null>(null);

  const saved = data?.content ?? "";
  const value = draft ?? saved;
  const dirtyDraft = draft !== null && draft !== saved ? draft : null;
  const isOpen = open ?? saved.trim().length > 0;

  const save = useCallback(
    (content: string) =>
      mutate(content, {
        // Only drop the draft if nothing was typed while this save was in flight
        onSuccess: () => setDraft((current) => (current === content ? null : current)),
      }),
    [mutate]
  );

  // Debounced autosave
  useEffect(() => {
    if (dirtyDraft === null) return;
    const timer = setTimeout(() => save(dirtyDraft), AUTOSAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [dirtyDraft, save]);

  const handleBlur = () => {
    if (dirtyDraft !== null) save(dirtyDraft);
  };

  const status = (
    <span className="flex items-center gap-1 text-xs text-muted-foreground" aria-live="polite">
      {dirtyDraft !== null || isPending ? (
        <>
          <Loader2 className="size-3 animate-spin" strokeWidth={1.5} />
          Saving
        </>
      ) : data?.updated_at ? (
        <>
          <Check className="size-3" strokeWidth={1.5} />
          Saved
        </>
      ) : null}
    </span>
  );

  const editor = (
    <div className="space-y-1.5">
      <Textarea
        size="sm"
        value={value}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={handleBlur}
        maxLength={MAX_LENGTH}
        disabled={isLoading}
        placeholder={isLoading ? "Loading notes…" : "Store hours, coupons, things to double-check…"}
        aria-label="Shopping list notes"
        className="max-h-64 overflow-y-auto"
      />
      {value.length > MAX_LENGTH * 0.9 && (
        <p className="text-xs text-right text-muted-foreground tabular-nums">
          {value.length} / {MAX_LENGTH}
        </p>
      )}
    </div>
  );

  if (variant === "card") {
    return (
      <Card className={cn("p-4 gap-3", className)}>
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold tracking-wider uppercase text-muted-foreground">
            Notes
          </h2>
          {status}
        </div>
        {editor}
      </Card>
    );
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setOpen} className={className}>
      <Card className="p-2 gap-0">
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="w-full justify-between">
            <span className="flex items-center gap-2 min-w-0">
              <NotebookPen className="size-4 shrink-0" strokeWidth={1.5} />
              Notes
              {!isOpen && saved.trim() && (
                <span className="font-normal truncate text-muted-foreground">
                  {saved.trim().split("\n")[0]}
                </span>
              )}
            </span>
            <span className="flex items-center gap-2 shrink-0">
              {isOpen && status}
              <ChevronDown
                className={cn("size-4 transition-transform", isOpen && "rotate-180")}
                strokeWidth={1.5}
              />
            </span>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="px-2 pt-2 pb-1">{editor}</CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
