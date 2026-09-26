"use client";

import { useState } from "react";
import { Loader2, Plus, RotateCcw, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAddSampleData, useRemoveSampleData, useSampleDataStatus } from "@/hooks/api";
import { getErrorMessage } from "@/lib/utils";

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

/**
 * SampleData — remove the onboarding starter pack new accounts are seeded
 * with (keeping anything the user edited), or add it back.
 */
export function SampleData() {
  const { data: status, isLoading, isError, refetch, isFetching } = useSampleDataStatus();
  const addSampleData = useAddSampleData();
  const removeSampleData = useRemoveSampleData();
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const handleRemove = () => {
    removeSampleData.mutate(undefined, {
      onSuccess: (result) => {
        const kept =
          result.recipes_kept > 0
            ? ` Kept ${plural(result.recipes_kept, "recipe")} you've been using.`
            : "";
        toast.success(
          `Removed ${plural(result.recipes_removed, "sample recipe")} and ${plural(result.meals_removed, "meal")}.${kept}`
        );
        setShowConfirmDialog(false);
      },
      onError: (error) => toast.error(getErrorMessage(error, "Failed to remove sample data")),
    });
  };

  const handleAdd = () => {
    addSampleData.mutate(undefined, {
      onSuccess: (result) =>
        toast.success(
          `Added ${plural(result.recipes_created, "sample recipe")} and ${plural(result.meals_created, "meal")}.`
        ),
      onError: (error) => toast.error(getErrorMessage(error, "Failed to add sample data")),
    });
  };

  const hasSampleData = status?.has_sample_data ?? false;

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" strokeWidth={1.5} />
          <Label className="text-base font-medium">Sample Data</Label>
        </div>

        {isLoading ? (
          <Skeleton className="h-10 w-full" />
        ) : isError ? (
          <>
            <p className="text-sm text-muted-foreground">
              Couldn&apos;t check your sample data right now.
            </p>
            <Button
              variant="outline"
              onClick={() => void refetch()}
              disabled={isFetching}
              className="gap-2"
            >
              {isFetching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" strokeWidth={1.5} />
              )}
              Try Again
            </Button>
          </>
        ) : hasSampleData ? (
          <>
            <p className="text-sm text-muted-foreground">
              Your account came with {plural(status?.recipe_count ?? 0, "sample recipe")} and{" "}
              {plural(status?.meal_count ?? 0, "meal")} to explore. Remove them when you&apos;re
              ready — anything you&apos;ve edited stays.
            </p>
            <Button
              variant="outline"
              onClick={() => setShowConfirmDialog(true)}
              className="gap-2"
            >
              <Trash2 className="h-4 w-4" strokeWidth={1.5} />
              Remove Sample Data
            </Button>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              Add a starter set of recipes, saved meals, and a planned week to explore the app.
            </p>
            <Button
              variant="outline"
              onClick={handleAdd}
              disabled={addSampleData.isPending}
              className="gap-2"
            >
              {addSampleData.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" strokeWidth={1.5} />
              )}
              Add Sample Data
            </Button>
          </>
        )}
      </div>

      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove sample data?</DialogTitle>
            <DialogDescription>
              This removes the sample recipes and meals your account started with, their
              planner entries, and their shopping list items.
            </DialogDescription>
          </DialogHeader>

          <p className="text-sm text-muted-foreground">
            Anything you&apos;ve made your own is kept: sample recipes or meals you&apos;ve edited,
            cooked, favorited, grouped, added a photo to, or used in your own meals.
          </p>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowConfirmDialog(false)}
              disabled={removeSampleData.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRemove}
              disabled={removeSampleData.isPending}
              className="gap-2"
            >
              {removeSampleData.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" strokeWidth={1.5} />
              )}
              Remove Sample Data
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
