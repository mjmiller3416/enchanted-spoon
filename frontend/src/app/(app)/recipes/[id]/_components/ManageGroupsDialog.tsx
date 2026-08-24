"use client";

import { useState } from "react";
import { FolderOpen, Plus, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { InlineGroupCreator } from "@/components/common/InlineGroupCreator";
import {
  useRecipeGroups,
  useRecipeGroupsForRecipe,
  useAssignRecipeToGroups,
  useCreateRecipeGroup,
} from "@/hooks/api/useRecipeGroups";

interface ManageGroupsDialogProps {
  recipeId: number;
  recipeName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ManageGroupsDialog({
  recipeId,
  recipeName,
  open,
  onOpenChange,
}: ManageGroupsDialogProps) {
  const [selectedGroupIds, setSelectedGroupIds] = useState<Set<number>>(new Set());
  const [isCreating, setIsCreating] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [isInitialized, setIsInitialized] = useState(false);

  // Fetch all groups and groups for this recipe
  const { data: allGroups = [], isLoading: isLoadingGroups } = useRecipeGroups();
  const { data: recipeGroups = [], isLoading: isLoadingRecipeGroups } =
    useRecipeGroupsForRecipe(recipeId);

  // Mutations
  const assignMutation = useAssignRecipeToGroups();
  const createMutation = useCreateRecipeGroup();

  // Initialize selection from the recipe's groups when the dialog opens, and
  // re-arm when it closes (guarded adjust-state-during-render pattern).
  if (open && !isInitialized) {
    setSelectedGroupIds(new Set(recipeGroups.map((g) => g.id)));
    setIsInitialized(true);
  } else if (!open && isInitialized) {
    setIsInitialized(false);
  }

  const handleToggleGroup = (groupId: number) => {
    const newSelected = new Set(selectedGroupIds);
    if (newSelected.has(groupId)) {
      newSelected.delete(groupId);
    } else {
      newSelected.add(groupId);
    }
    setSelectedGroupIds(newSelected);
  };

  const handleCreateGroup = () => {
    const trimmedName = newGroupName.trim();
    if (!trimmedName) return;

    createMutation.mutate(
      { name: trimmedName },
      {
        onSuccess: (newGroup) => {
          // Add the newly created group to selection
          const newSelected = new Set(selectedGroupIds);
          newSelected.add(newGroup.id);
          setSelectedGroupIds(newSelected);
          setNewGroupName("");
          setIsCreating(false);
          toast.success(`Group "${trimmedName}" created`);
        },
        onError: () => {
          toast.error("Failed to create group");
        },
      }
    );
  };

  const handleSave = () => {
    assignMutation.mutate(
      {
        recipeId,
        data: { group_ids: Array.from(selectedGroupIds) },
      },
      {
        onSuccess: () => {
          toast.success("Recipe groups updated");
          onOpenChange(false);
        },
        onError: () => {
          toast.error("Failed to update recipe groups");
        },
      }
    );
  };

  const isLoading = isLoadingGroups || isLoadingRecipeGroups;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FolderOpen className="size-5 text-primary" strokeWidth={1.5} />
            Manage Recipe Groups
          </DialogTitle>
          <DialogDescription>
            Organize &quot;{recipeName}&quot; into custom groups for easier filtering
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Groups List */}
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={1.5} />
            </div>
          ) : (
            <>
              {allGroups.length > 0 ? (
                <Card className="border-dashed">
                  <CardContent className="p-3 space-y-2">
                    {allGroups.map((group) => (
                      <div
                        key={group.id}
                        className="flex items-center gap-3 px-2 py-1.5 rounded-md hover:bg-hover transition-colors"
                      >
                        <Checkbox
                          id={`group-${group.id}`}
                          checked={selectedGroupIds.has(group.id)}
                          onCheckedChange={() => handleToggleGroup(group.id)}
                        />
                        <Label
                          htmlFor={`group-${group.id}`}
                          className="flex-1 cursor-pointer text-sm font-medium"
                        >
                          {group.name}
                        </Label>
                        <span className="text-xs text-muted-foreground">
                          {group.recipe_count} {group.recipe_count === 1 ? "recipe" : "recipes"}
                        </span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ) : (
                !isCreating && (
                  <div className="text-center py-6">
                    <div className="rounded-full bg-muted p-4 inline-flex mb-3">
                      <FolderOpen className="size-8 text-muted-foreground" strokeWidth={1.5} />
                    </div>
                    <h3 className="text-sm font-semibold">No groups yet</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Create your first group below
                    </p>
                  </div>
                )
              )}

              {/* Create New Group */}
              {isCreating ? (
                <InlineGroupCreator
                  value={newGroupName}
                  onChange={setNewGroupName}
                  onSubmit={handleCreateGroup}
                  onCancel={() => {
                    setIsCreating(false);
                    setNewGroupName("");
                  }}
                  isPending={createMutation.isPending}
                />
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsCreating(true)}
                  className="w-full"
                >
                  <Plus className="size-4 mr-2" strokeWidth={1.5} />
                  Create New Group
                </Button>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={assignMutation.isPending || isLoading}
          >
            {assignMutation.isPending ? (
              <>
                <Loader2 className="size-4 mr-2 animate-spin" strokeWidth={1.5} />
                Saving...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
