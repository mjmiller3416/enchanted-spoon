"use client";

import { useState, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { invalidateRecipeDependents } from "@/hooks/api/invalidateRecipeDependents";
import { useAuth } from "@clerk/nextjs";
import {
  Upload,
  Download,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { dataManagementApi, recipeApi } from "@/lib/api";
import { getErrorMessage, downloadBlob } from "@/lib/utils";
import type {
  ImportPreviewDTO,
  ImportResultDTO,
  DuplicateResolutionDTO,
  DuplicateAction,
  DuplicateRecipeDTO,
} from "@/types/common";

// ============================================================================
// DUPLICATE RESOLUTION ROW
// ============================================================================

interface DuplicateResolutionRowProps {
  duplicate: DuplicateRecipeDTO;
  resolution: DuplicateResolutionDTO;
  onResolutionChange: (resolution: DuplicateResolutionDTO) => void;
}

function DuplicateResolutionRow({
  duplicate,
  resolution,
  onResolutionChange,
}: DuplicateResolutionRowProps) {
  return (
    <div className="flex flex-col gap-2 p-3 bg-elevated rounded-lg border border-border">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium text-foreground">{duplicate.recipe_name}</p>
          <p className="text-xs text-muted-foreground">
            Category: {duplicate.recipe_category} (Row {duplicate.row_number})
          </p>
        </div>
        <Select
          value={resolution.action}
          onValueChange={(value: DuplicateAction) =>
            onResolutionChange({ ...resolution, action: value })
          }
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="skip">Skip</SelectItem>
            <SelectItem value="update">Update</SelectItem>
            <SelectItem value="rename">Rename</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {resolution.action === "rename" && (
        <Input
          placeholder="New recipe name"
          value={resolution.new_name || ""}
          onChange={(e) =>
            onResolutionChange({ ...resolution, new_name: e.target.value })
          }
          className="mt-1"
        />
      )}
    </div>
  );
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export function ExportImport() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  // Import state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [importPreview, setImportPreview] = useState<ImportPreviewDTO | null>(null);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [resolutions, setResolutions] = useState<DuplicateResolutionDTO[]>([]);
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResultDTO | null>(null);
  const [showResultDialog, setShowResultDialog] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportFavoritesOnly, setExportFavoritesOnly] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");

  // Template state
  const [isDownloadingTemplate, setIsDownloadingTemplate] = useState(false);

  // ── Import Handlers ──────────────────────────────────────────────────────

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith(".xlsx")) {
        toast.error("Please select an .xlsx file");
        return;
      }
      setImportFile(file);
    }
  };

  const handlePreviewImport = async () => {
    if (!importFile) {
      toast.error("Please select a file first");
      return;
    }

    setIsPreviewLoading(true);
    try {
      const token = await getToken();
      const preview = await dataManagementApi.previewImport(importFile, token);
      setImportPreview(preview);

      const initialResolutions: DuplicateResolutionDTO[] =
        preview.duplicate_recipes.map((dup) => ({
          recipe_name: dup.recipe_name,
          recipe_category: dup.recipe_category,
          action: "skip" as DuplicateAction,
        }));
      setResolutions(initialResolutions);

      setShowPreviewDialog(true);
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to preview import"));
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleExecuteImport = async () => {
    if (!importFile || !importPreview) return;

    for (const res of resolutions) {
      if (res.action === "rename" && !res.new_name?.trim()) {
        toast.error(`Please provide a new name for "${res.recipe_name}"`);
        return;
      }
    }

    setIsImporting(true);
    try {
      const token = await getToken();
      const result = await dataManagementApi.executeImport(importFile, resolutions, token);
      await invalidateRecipeDependents(queryClient);
      setImportResult(result);
      setShowPreviewDialog(false);
      setShowResultDialog(true);

      if (result.success) {
        toast.success(
          `Import complete: ${result.created_count} created, ${result.updated_count} updated`
        );
      } else {
        toast.warning("Import completed with some errors");
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to execute import"));
    } finally {
      setIsImporting(false);
    }
  };

  const handleCloseResultDialog = () => {
    setShowResultDialog(false);
    setImportResult(null);
    setImportFile(null);
    setImportPreview(null);
    setResolutions([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const updateResolution = (index: number, newRes: DuplicateResolutionDTO) => {
    const updated = [...resolutions];
    updated[index] = newRes;
    setResolutions(updated);
  };

  // ── Export Handlers ──────────────────────────────────────────────────────

  const loadCategories = useCallback(async () => {
    try {
      const token = await getToken();
      const cats = await recipeApi.getCategories(token);
      setCategories(cats);
    } catch {
      // Silently fail - categories are optional
    }
  }, [getToken]);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const token = await getToken();
      const blob = await dataManagementApi.exportRecipes({
        favorites_only: exportFavoritesOnly,
        recipe_category: selectedCategory || null,
      }, token);

      downloadBlob(blob, `recipes_export_${new Date().toISOString().split("T")[0]}.xlsx`);

      toast.success("Recipes exported successfully");
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to export recipes"));
    } finally {
      setIsExporting(false);
    }
  };

  // ── Template Handler ─────────────────────────────────────────────────────

  const handleDownloadTemplate = async () => {
    setIsDownloadingTemplate(true);
    try {
      const token = await getToken();
      const blob = await dataManagementApi.downloadTemplate(token);

      downloadBlob(blob, "recipe_import_template.xlsx");

      toast.success("Template downloaded");
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to download template"));
    } finally {
      setIsDownloadingTemplate(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <>
      <div className="space-y-6">
        {/* Import Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Upload className="h-4 w-4 text-muted-foreground" />
            <Label className="text-base font-medium">Import Recipes (Excel)</Label>
          </div>
          <p className="text-sm text-muted-foreground">
            Upload an Excel file (.xlsx) to import recipes into your collection.
          </p>
          <div className="flex items-center gap-3">
            <Input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              onChange={handleFileSelect}
              className="max-w-xs"
            />
            <Button
              onClick={handlePreviewImport}
              disabled={!importFile || isPreviewLoading}
              className="gap-2"
            >
              {isPreviewLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Preview Import
            </Button>
          </div>
          {importFile && (
            <p className="text-sm text-muted-foreground">
              Selected: {importFile.name}
            </p>
          )}
        </div>

        <Separator />

        {/* Export Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Download className="h-4 w-4 text-muted-foreground" />
            <Label className="text-base font-medium">Export Recipes (Excel)</Label>
          </div>
          <p className="text-sm text-muted-foreground">
            Download your recipes as an Excel file for backup or sharing.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Checkbox
                id="favoritesOnly"
                checked={exportFavoritesOnly}
                onCheckedChange={(checked) =>
                  setExportFavoritesOnly(checked === true)
                }
              />
              <Label htmlFor="favoritesOnly" className="text-sm cursor-pointer">
                Favorites only
              </Label>
            </div>
            <Select
              value={selectedCategory || "all"}
              onValueChange={(val) => setSelectedCategory(val === "all" ? "" : val)}
              onOpenChange={(open) => open && loadCategories()}
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              onClick={handleExport}
              disabled={isExporting}
              variant="outline"
              className="gap-2"
            >
              {isExporting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Export to XLSX
            </Button>
          </div>
        </div>

        <Separator />

        {/* Template Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
            <Label className="text-base font-medium">Import Template</Label>
          </div>
          <p className="text-sm text-muted-foreground">
            Download a template file to see the expected format for importing recipes.
            The template includes example data and all required columns.
          </p>
          <Button
            onClick={handleDownloadTemplate}
            disabled={isDownloadingTemplate}
            variant="outline"
            className="gap-2"
          >
            {isDownloadingTemplate ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileSpreadsheet className="h-4 w-4" />
            )}
            Download Template
          </Button>
        </div>
      </div>

      {/* Import Preview Dialog */}
      <Dialog open={showPreviewDialog} onOpenChange={setShowPreviewDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Import Preview</DialogTitle>
            <DialogDescription>
              Review the recipes that will be imported
            </DialogDescription>
          </DialogHeader>

          {importPreview && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-2xl font-bold text-foreground">
                    {importPreview.total_recipes}
                  </p>
                  <p className="text-xs text-muted-foreground">Total Recipes</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-2xl font-bold text-success">
                    {importPreview.new_recipes}
                  </p>
                  <p className="text-xs text-muted-foreground">New Recipes</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-2xl font-bold text-warning">
                    {importPreview.duplicate_recipes.length}
                  </p>
                  <p className="text-xs text-muted-foreground">Duplicates</p>
                </div>
              </div>

              {/* Validation Errors */}
              {importPreview.validation_errors.length > 0 && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-destructive" />
                    <p className="font-medium text-destructive">Validation Errors</p>
                  </div>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {importPreview.validation_errors.map((err, i) => (
                      <li key={i}>
                        Row {err.row_number}: {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Duplicate Resolutions */}
              {importPreview.duplicate_recipes.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                    <p className="font-medium text-foreground">
                      Handle Duplicate Recipes
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    These recipes already exist. Choose how to handle each one:
                  </p>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {importPreview.duplicate_recipes.map((dup, index) => (
                      <DuplicateResolutionRow
                        key={`${dup.recipe_name}-${dup.recipe_category}`}
                        duplicate={dup}
                        resolution={resolutions[index]}
                        onResolutionChange={(res) => updateResolution(index, res)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowPreviewDialog(false)}
              disabled={isImporting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleExecuteImport}
              disabled={isImporting || (importPreview?.total_recipes === 0)}
              className="gap-2"
            >
              {isImporting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Import Recipes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Result Dialog */}
      <Dialog open={showResultDialog} onOpenChange={setShowResultDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {importResult?.success ? (
                <CheckCircle2 className="h-5 w-5 text-success" />
              ) : (
                <XCircle className="h-5 w-5 text-destructive" />
              )}
              Import {importResult?.success ? "Complete" : "Completed with Errors"}
            </DialogTitle>
          </DialogHeader>

          {importResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-2xl font-bold text-success">
                    {importResult.created_count}
                  </p>
                  <p className="text-xs text-muted-foreground">Created</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-2xl font-bold text-info">
                    {importResult.updated_count}
                  </p>
                  <p className="text-xs text-muted-foreground">Updated</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-2xl font-bold text-muted-foreground">
                    {importResult.skipped_count}
                  </p>
                  <p className="text-xs text-muted-foreground">Skipped</p>
                </div>
              </div>

              {importResult.errors.length > 0 && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-destructive" />
                    <p className="font-medium text-destructive">Errors</p>
                  </div>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {importResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button onClick={handleCloseResultDialog}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
