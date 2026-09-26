"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useQueryClient } from "@tanstack/react-query";
import { Trash2, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { dataManagementApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";

export function DeleteData() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();
  const [showDeleteConfirmDialog, setShowDeleteConfirmDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteAll = async () => {
    setIsDeleting(true);
    try {
      const token = await getToken();
      const result = await dataManagementApi.clearAllData(token);
      if (result.success) {
        const totalDeleted = Object.values(result.deleted_counts).reduce(
          (sum, count) => sum + count,
          0
        );
        toast.success(`All data deleted (${totalDeleted} records removed)`);
        setShowDeleteConfirmDialog(false);
        // Every cached list (recipes, menu, shopping badge, sample status…) is now stale
        await queryClient.invalidateQueries();
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to delete data"));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Trash2 className="h-4 w-4 text-destructive" />
          <Label className="text-base font-medium text-destructive">
            Delete All Data
          </Label>
        </div>
        <p className="text-sm text-muted-foreground">
          Permanently delete all recipes, ingredients, meal plans, and shopping lists.
          This action cannot be undone.
        </p>
        <Button
          onClick={() => setShowDeleteConfirmDialog(true)}
          variant="destructive"
          className="gap-2"
        >
          <Trash2 className="h-4 w-4" />
          Delete All Data
        </Button>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteConfirmDialog} onOpenChange={setShowDeleteConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Confirm Delete All Data
            </DialogTitle>
            <DialogDescription>
              This will permanently delete all data including:
            </DialogDescription>
          </DialogHeader>

          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside ml-2">
            <li>All recipes and their ingredients</li>
            <li>All recipe images (from Cloudinary)</li>
            <li>All meal plans and planner entries</li>
            <li>All shopping lists and items</li>
            <li>All saved ingredients</li>
          </ul>

          <p className="text-sm font-medium text-destructive">
            This action cannot be undone!
          </p>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteConfirmDialog(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteAll}
              disabled={isDeleting}
              className="gap-2"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Delete Everything
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
