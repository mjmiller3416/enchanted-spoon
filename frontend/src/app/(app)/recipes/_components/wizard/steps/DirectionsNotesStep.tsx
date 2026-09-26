"use client";

import { useMemo, useCallback } from "react";
import { useFormContext, useFieldArray } from "react-hook-form";
import {
  DndContext,
  closestCenter,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Trash2, PlusCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { useSortableDnd } from "@/hooks/ui/useSortableDnd";
import { createEmptyDirection } from "../useRecipeWizard";
import type { WizardFormValues } from "../wizardSchema";

// ---------------------------------------------------------------------------
// Sortable Direction Row
// ---------------------------------------------------------------------------

const STEP_PLACEHOLDERS = [
  "e.g. Preheat the oven to 375 degrees...",
  "What's the next instruction?",
  "Keep going...",
];

interface DirectionRowProps {
  id: string;
  text: string;
  index: number;
  onUpdate: (index: number, text: string) => void;
  onDelete: (index: number) => void;
}

function SortableDirectionRow({
  id,
  text,
  index,
  onUpdate,
  onDelete,
}: DirectionRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const placeholder =
    STEP_PLACEHOLDERS[index % STEP_PLACEHOLDERS.length];

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "group bg-elevated hover:bg-hover transition-colors rounded-lg p-3 border border-border",
        isDragging && "opacity-50 shadow-lg"
      )}
    >
      <div className="flex items-start gap-3">
        {/* Drag handle */}
        <button
          type="button"
          className="p-1 mt-2 text-muted-foreground hover:text-foreground transition-colors cursor-grab active:cursor-grabbing shrink-0 touch-none"
          aria-label={`Drag to reorder step ${index + 1}`}
          {...attributes}
          {...listeners}
          tabIndex={-1}
        >
          <GripVertical className="size-5" strokeWidth={1.5} />
        </button>

        {/* Step content */}
        <div className="flex-1 min-w-0 space-y-1.5">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Step {index + 1}
          </span>
          <Label htmlFor={`direction-${id}`} className="sr-only">
            Step {index + 1} instructions
          </Label>
          <Textarea
            id={`direction-${id}`}
            value={text}
            onChange={(e) => onUpdate(index, e.target.value)}
            placeholder={placeholder}
            rows={3}
            className="resize-none"
          />
        </div>

        {/* Delete button */}
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="mt-2 shrink-0 text-muted-foreground hover:text-destructive"
          onClick={() => onDelete(index)}
          aria-label={`Delete step ${index + 1}`}
        >
          <Trash2 className="size-4" strokeWidth={1.5} />
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component (no props — everything from form context)
// ---------------------------------------------------------------------------

export function DirectionsNotesStep() {
  const form = useFormContext<WizardFormValues>();
  const { fields, append, remove, move } = useFieldArray({
    control: form.control,
    name: "directions",
  });

  const { sensors, modifiers } = useSortableDnd();
  const notes = form.watch("notes");
  const watchedDirections = form.watch("directions");

  const sortableIds = useMemo(
    () => fields.map((d) => d.id),
    [fields]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (over && active.id !== over.id) {
        const oldIndex = fields.findIndex((f) => f.id === String(active.id));
        const newIndex = fields.findIndex((f) => f.id === String(over.id));
        if (oldIndex !== -1 && newIndex !== -1) {
          move(oldIndex, newIndex);
        }
      }
    },
    [fields, move]
  );

  const handleUpdateDirection = useCallback(
    (index: number, text: string) => {
      form.setValue(`directions.${index}.text`, text, { shouldDirty: true });
    },
    [form]
  );

  const handleDeleteDirection = useCallback(
    (index: number) => {
      remove(index);
    },
    [remove]
  );

  // Root-level error (e.g. "At least one direction step is required")
  const rootError = (form.formState.errors.directions as { root?: { message?: string } } | undefined)?.root?.message
    ?? form.formState.errors.directions?.message;

  return (
    <Tabs defaultValue="directions" className="space-y-4">
      <TabsList>
        <TabsTrigger value="directions">Directions</TabsTrigger>
        <TabsTrigger value="notes">Notes</TabsTrigger>
      </TabsList>

      {/* ----------------------------------------------------------------- */}
      {/* Directions Tab                                                     */}
      {/* ----------------------------------------------------------------- */}
      <TabsContent value="directions" className="space-y-4">
        <DndContext
          sensors={sensors}
          modifiers={modifiers}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={sortableIds}
            strategy={verticalListSortingStrategy}
          >
            <div className="space-y-2">
              {fields.map((field, index) => (
                <SortableDirectionRow
                  key={field.id}
                  id={field.id}
                  text={watchedDirections?.[index]?.text ?? field.text}
                  index={index}
                  onUpdate={handleUpdateDirection}
                  onDelete={handleDeleteDirection}
                />
              ))}
            </div>
          </SortableContext>
        </DndContext>

        {/* Error message for directions */}
        {rootError && (
          <p className="text-sm text-destructive" role="alert">
            {rootError}
          </p>
        )}

        {/* Add Next Step button */}
        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={() => append(createEmptyDirection())}
        >
          <PlusCircle className="size-4 mr-2" strokeWidth={1.5} />
          Add Next Step
        </Button>
      </TabsContent>

      {/* ----------------------------------------------------------------- */}
      {/* Notes Tab                                                          */}
      {/* ----------------------------------------------------------------- */}
      <TabsContent value="notes" className="space-y-4">
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-foreground">
            Chef&apos;s Notes
          </h3>
          <p className="text-sm text-muted-foreground">
            Add context, tips, or personal touches to your recipe.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="wizard-notes" className="sr-only">
            Recipe notes
          </Label>
          <Textarea
            id="wizard-notes"
            value={notes}
            onChange={(e) => form.setValue("notes", e.target.value, { shouldDirty: true })}
            placeholder={[
              "Add helpful notes for this recipe, such as:",
              "  - Ingredient substitutions",
              "  - Serving suggestions",
              "  - Storage and reheating advice",
              "  - Dietary modification tips",
              "  - Where you discovered this recipe",
            ].join("\n")}
            rows={8}
          />
          <p className="text-xs text-muted-foreground">
            Markdown supported
          </p>
        </div>

        {/* Pro Tip Banner */}
        <div className="flex gap-3 bg-info/10 border border-info/20 rounded-lg p-4">
          <Info
            className="size-5 text-info shrink-0 mt-0.5"
            strokeWidth={1.5}
          />
          <div>
            <p className="text-sm font-medium text-foreground">Pro Tip</p>
            <p className="text-sm text-muted-foreground">
              Notes are a great place to explain <em>why</em> certain steps
              are important.
            </p>
          </div>
        </div>
      </TabsContent>
    </Tabs>
  );
}
