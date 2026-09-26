"use client";

import { useState } from "react";
import { ChefHat, Filter, RotateCcw, Plus, Edit2, Trash2, X, Check, Loader2, FolderOpen } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { cn, getErrorMessage } from "@/lib/utils";
import { QUICK_FILTERS, DEFAULT_QUICK_FILTER_IDS } from "@/lib/constants";
import { SectionHeader } from "../SectionHeader";
import { InlineGroupCreator } from "@/components/common/InlineGroupCreator";
import {
  useRecipeGroups,
  useCreateRecipeGroup,
  useUpdateRecipeGroup,
  useDeleteRecipeGroup,
} from "@/hooks/api/useRecipeGroups";
import { RecipeCategoriesSection } from "./RecipeCategoriesSection";
import { IngredientCategoriesSection } from "./IngredientCategoriesSection";

const MAX_FILTERS = 5;

interface RecipePreferencesSectionProps {
  quickFilters: string[];
  onQuickFiltersChange: (filters: string[]) => void;
}

interface RecipeGroupItemProps {
  name: string;
  recipeCount: number;
  isEditing: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onSave: (name: string) => void;
  onCancel: () => void;
}

function RecipeGroupItem({
  name,
  recipeCount,
  isEditing,
  onEdit,
  onDelete,
  onSave,
  onCancel,
}: RecipeGroupItemProps) {
  const [editValue, setEditValue] = useState(name);

  const handleSave = () => {
    const trimmedValue = editValue.trim();
    if (trimmedValue && trimmedValue !== name) {
      onSave(trimmedValue);
    } else {
      onCancel();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave();
    } else if (e.key === "Escape") {
      onCancel();
    }
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-card border border-border">
        <FolderOpen className="size-4 text-muted-foreground shrink-0" strokeWidth={1.5} />
        <Input
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="h-8 flex-1"
          placeholder="Group name"
          autoFocus
          maxLength={255}
        />
        <div className="flex items-center gap-1 shrink-0">
          <Button
            size="icon"
            variant="ghost"
            className="h-8 w-8"
            onClick={handleSave}
            aria-label="Save group name"
          >
            <Check className="size-4" strokeWidth={1.5} />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="h-8 w-8"
            onClick={onCancel}
            aria-label="Cancel editing"
          >
            <X className="size-4" strokeWidth={1.5} />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-card hover:bg-hover border border-border transition-colors">
      <FolderOpen className="size-4 text-muted-foreground shrink-0" strokeWidth={1.5} />
      <span className="text-sm font-medium flex-1 truncate">{name}</span>
      <Badge variant="secondary" className="shrink-0">
        {recipeCount}
      </Badge>
      <div className="flex items-center gap-1 shrink-0">
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8"
          onClick={onEdit}
          aria-label={`Edit ${name}`}
        >
          <Edit2 className="size-4" strokeWidth={1.5} />
        </Button>
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8"
          onClick={onDelete}
          aria-label={`Delete ${name}`}
        >
          <Trash2 className="size-4" strokeWidth={1.5} />
        </Button>
      </div>
    </div>
  );
}

export function RecipePreferencesSection({
  quickFilters,
  onQuickFiltersChange,
}: RecipePreferencesSectionProps) {
  const selectedCount = quickFilters.length;
  const isAtLimit = selectedCount >= MAX_FILTERS;

  // Recipe groups state
  const [isAdding, setIsAdding] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{
    id: number;
    name: string;
  } | null>(null);

  // Queries and mutations
  const { data: groups = [], isLoading } = useRecipeGroups();
  const createMutation = useCreateRecipeGroup();
  const updateMutation = useUpdateRecipeGroup();
  const deleteMutation = useDeleteRecipeGroup();

  const toggleFilter = (filterId: string) => {
    const isSelected = quickFilters.includes(filterId);

    if (isSelected) {
      // Remove filter
      onQuickFiltersChange(quickFilters.filter((id) => id !== filterId));
    } else if (!isAtLimit) {
      // Add filter (only if under limit)
      onQuickFiltersChange([...quickFilters, filterId]);
    }
  };

  const resetToDefaults = () => {
    onQuickFiltersChange([...DEFAULT_QUICK_FILTER_IDS]);
  };

  const handleAddGroup = () => {
    const trimmedName = newGroupName.trim();
    if (!trimmedName) return;

    createMutation.mutate(
      { name: trimmedName },
      {
        onSuccess: () => {
          setNewGroupName("");
          setIsAdding(false);
        },
        onError: (error) => toast.error(getErrorMessage(error, "Couldn't create the group")),
      }
    );
  };

  const handleUpdateGroup = (id: number, name: string) => {
    updateMutation.mutate(
      { id, data: { name } },
      {
        onSuccess: () => {
          setEditingId(null);
        },
      }
    );
  };

  const handleDeleteGroup = () => {
    if (!deleteConfirm) return;

    deleteMutation.mutate(deleteConfirm.id, {
      onSuccess: () => {
        setDeleteConfirm(null);
      },
    });
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={ChefHat}
          title="Recipe Preferences"
          description="Customize how you browse and discover recipes"
          accentColor="primary"
        />

        <div className="space-y-6">
          {/* Quick Filters Selection */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="flex items-center gap-2">
                <Filter className="h-3.5 w-3.5 text-muted-foreground" />
                Quick Filters
              </Label>
              <Badge variant="secondary" className="text-xs">
                {selectedCount} of {MAX_FILTERS} selected
              </Badge>
            </div>

            <p className="text-xs text-muted-foreground">
              Choose up to {MAX_FILTERS} filters to display in the recipe browser
            </p>

            {/* Filter Toggle Grid */}
            <div className="flex flex-wrap gap-2">
              {QUICK_FILTERS.map((filter) => {
                const isSelected = quickFilters.includes(filter.id);
                const isDisabled = !isSelected && isAtLimit;

                return (
                  <button
                    key={filter.id}
                    onClick={() => toggleFilter(filter.id)}
                    disabled={isDisabled}
                    className={cn(
                      "px-4 py-2 rounded-full border-2 text-sm font-medium transition-all duration-150",
                      isSelected
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-card text-muted-foreground hover:border-muted hover:bg-hover",
                      isDisabled && "opacity-40 cursor-not-allowed"
                    )}
                  >
                    {filter.label}
                  </button>
                );
              })}
            </div>

            {/* Reset Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={resetToDefaults}
              className="mt-2"
            >
              <RotateCcw className="h-3.5 w-3.5 mr-2" />
              Reset to Defaults
            </Button>
          </div>

          {/* Divider */}
          <div className="border-t border-border" />

          {/* Recipe Groups Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label className="flex items-center gap-2">
                <FolderOpen className="size-3.5 text-muted-foreground" strokeWidth={1.5} />
                Recipe Groups
              </Label>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsAdding(true)}
                disabled={isAdding}
              >
                <Plus className="size-4 mr-1.5" strokeWidth={1.5} />
                New Group
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              Create custom groups to organize your recipes (e.g., &quot;Weeknight Favorites&quot;,
              &quot;Holiday Meals&quot;). Assign recipes to groups from the recipe details page.
            </p>

            <Card className="border-dashed">
              <CardContent className="p-2">
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={1.5} />
                  </div>
                ) : (
                  <div className="space-y-1">
                    {/* Add new group input */}
                    {isAdding && (
                      <InlineGroupCreator
                        value={newGroupName}
                        onChange={setNewGroupName}
                        onSubmit={handleAddGroup}
                        onCancel={() => {
                          setIsAdding(false);
                          setNewGroupName("");
                        }}
                        isPending={createMutation.isPending}
                        size="sm"
                      />
                    )}

                    {/* Existing groups */}
                    {groups.length === 0 && !isAdding ? (
                      <div className="text-center py-8">
                        <div className="rounded-full bg-muted p-4 inline-flex mb-3">
                          <FolderOpen className="size-8 text-muted-foreground" strokeWidth={1.5} />
                        </div>
                        <h3 className="text-sm font-semibold">No groups yet</h3>
                        <p className="text-xs text-muted-foreground mt-1">
                          Create your first group to organize recipes
                        </p>
                      </div>
                    ) : (
                      groups.map((group) => (
                        <RecipeGroupItem
                          key={group.id}
                          name={group.name}
                          recipeCount={group.recipe_count}
                          isEditing={editingId === group.id}
                          onEdit={() => setEditingId(group.id)}
                          onDelete={() => setDeleteConfirm({ id: group.id, name: group.name })}
                          onSave={(name) => handleUpdateGroup(group.id, name)}
                          onCancel={() => setEditingId(null)}
                        />
                      ))
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Divider */}
          <div className="border-t border-border" />

          {/* Recipe Categories Section */}
          <RecipeCategoriesSection />

          {/* Divider */}
          <div className="border-t border-border" />

          {/* Ingredient Categories Section */}
          <IngredientCategoriesSection />
        </div>
      </CardContent>

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Recipe Group</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{deleteConfirm?.name}&quot;? This will not
              delete any recipes, only the group itself.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteGroup}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="size-4 mr-2 animate-spin" strokeWidth={1.5} />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
