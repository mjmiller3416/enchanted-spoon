"use client";

import { useState, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  Download,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
  HardDrive,
  RotateCcw,
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
import { dataManagementApi } from "@/lib/api";
import { getErrorMessage, downloadBlob } from "@/lib/utils";
import { useSettings, SETTINGS_STORAGE_KEY } from "@/hooks/persistence/useSettings";
import type { RestorePreview, RestoreResult } from "@/types/common";

export function BackupRestore() {
  const { getToken } = useAuth();
  const { settings } = useSettings();

  // Full backup state
  const [isCreatingBackup, setIsCreatingBackup] = useState(false);
  const [includeSettings, setIncludeSettings] = useState(true);

  // Restore state
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [isPreviewingRestore, setIsPreviewingRestore] = useState(false);
  const [restorePreview, setRestorePreview] = useState<RestorePreview | null>(null);
  const [showRestorePreviewDialog, setShowRestorePreviewDialog] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [showRestoreResultDialog, setShowRestoreResultDialog] = useState(false);
  const [restoreResult, setRestoreResult] = useState<RestoreResult | null>(null);
  const restoreFileInputRef = useRef<HTMLInputElement>(null);

  // ── Full Backup Handler ──────────────────────────────────────────────────

  const handleCreateFullBackup = async () => {
    setIsCreatingBackup(true);
    try {
      const token = await getToken();
      const backup = await dataManagementApi.exportFullBackup(token);

      if (includeSettings) {
        backup.settings = settings as unknown as Record<string, unknown>;
      }

      const blob = new Blob([JSON.stringify(backup, null, 2)], {
        type: "application/json",
      });
      downloadBlob(blob, `meal-genie-backup-${new Date().toISOString().split("T")[0]}.json`);

      toast.success("Full backup created successfully");
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to create backup"));
    } finally {
      setIsCreatingBackup(false);
    }
  };

  // ── Restore Handlers ─────────────────────────────────────────────────────

  const handleRestoreFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith(".json")) {
        toast.error("Please select a .json backup file");
        return;
      }
      setRestoreFile(file);
    }
  };

  const handlePreviewRestore = async () => {
    if (!restoreFile) {
      toast.error("Please select a backup file first");
      return;
    }

    setIsPreviewingRestore(true);
    try {
      const token = await getToken();
      const preview = await dataManagementApi.previewRestore(restoreFile, token);
      setRestorePreview(preview);
      setShowRestorePreviewDialog(true);
    } catch (error) {
      toast.error(getErrorMessage(error, "Invalid backup file"));
    } finally {
      setIsPreviewingRestore(false);
    }
  };

  const handleExecuteRestore = async () => {
    if (!restoreFile) return;

    setIsRestoring(true);
    try {
      const token = await getToken();
      const result = await dataManagementApi.executeRestore(restoreFile, true, token);

      if (result.settings) {
        localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(result.settings));
        window.dispatchEvent(new CustomEvent("settings-updated", { detail: result.settings }));
      }

      setRestoreResult(result);
      setShowRestorePreviewDialog(false);
      setShowRestoreResultDialog(true);

      if (result.success) {
        toast.success("Restore completed successfully");
      } else {
        toast.warning("Restore completed with some errors");
      }
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to restore backup"));
    } finally {
      setIsRestoring(false);
    }
  };

  const handleCloseRestoreResultDialog = () => {
    setShowRestoreResultDialog(false);
    setRestoreResult(null);
    setRestoreFile(null);
    setRestorePreview(null);
    if (restoreFileInputRef.current) {
      restoreFileInputRef.current.value = "";
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <>
      <div className="space-y-6">
        {/* Full Backup Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <HardDrive className="h-4 w-4 text-muted-foreground" />
            <Label className="text-base font-medium">Full Backup</Label>
          </div>
          <p className="text-sm text-muted-foreground">
            Create a complete backup of all your data including recipes, meals, planner
            entries, shopping lists, and optionally your app settings.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Checkbox
                id="includeSettings"
                checked={includeSettings}
                onCheckedChange={(checked) => setIncludeSettings(checked === true)}
              />
              <Label htmlFor="includeSettings" className="text-sm cursor-pointer">
                Include app settings
              </Label>
            </div>
            <Button
              onClick={handleCreateFullBackup}
              disabled={isCreatingBackup}
              className="gap-2"
            >
              {isCreatingBackup ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Create Full Backup
            </Button>
          </div>
        </div>

        <Separator />

        {/* Restore Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <RotateCcw className="h-4 w-4 text-muted-foreground" />
            <Label className="text-base font-medium">Restore from Backup</Label>
          </div>
          <p className="text-sm text-muted-foreground">
            Restore your data from a previously created backup file. This will replace
            all existing data.
          </p>
          <div className="flex items-center gap-3">
            <Input
              ref={restoreFileInputRef}
              type="file"
              accept=".json"
              onChange={handleRestoreFileSelect}
              className="max-w-xs"
            />
            <Button
              onClick={handlePreviewRestore}
              disabled={!restoreFile || isPreviewingRestore}
              variant="outline"
              className="gap-2"
            >
              {isPreviewingRestore ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              Preview Restore
            </Button>
          </div>
          {restoreFile && (
            <p className="text-sm text-muted-foreground">Selected: {restoreFile.name}</p>
          )}
        </div>
      </div>

      {/* Restore Preview Dialog */}
      <Dialog open={showRestorePreviewDialog} onOpenChange={setShowRestorePreviewDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Restore Preview</DialogTitle>
            <DialogDescription>Review what will be restored from your backup</DialogDescription>
          </DialogHeader>

          {restorePreview && (
            <div className="space-y-4">
              {/* Backup Info */}
              <div className="p-3 bg-elevated rounded-lg">
                <p className="text-sm text-muted-foreground">
                  Backup version: <span className="text-foreground">{restorePreview.backup_version}</span>
                </p>
                <p className="text-sm text-muted-foreground">
                  Created: <span className="text-foreground">
                    {new Date(restorePreview.backup_created_at).toLocaleString()}
                  </span>
                </p>
                <p className="text-sm text-muted-foreground">
                  Includes settings: <span className="text-foreground">
                    {restorePreview.has_settings ? "Yes" : "No"}
                  </span>
                </p>
              </div>

              {/* Counts */}
              <div className="grid grid-cols-4 gap-3">
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-foreground">
                    {restorePreview.counts.recipes || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Recipes</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-foreground">
                    {restorePreview.counts.meals || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Meals</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-foreground">
                    {restorePreview.counts.planner_entries || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Planner</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-foreground">
                    {restorePreview.counts.shopping_items || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Shopping</p>
                </div>
              </div>

              {/* Warnings */}
              {restorePreview.warnings.length > 0 && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-amber-500" />
                    <p className="font-medium text-amber-500">Warnings</p>
                  </div>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {restorePreview.warnings.map((warning, i) => (
                      <li key={i}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <p className="text-sm text-destructive">
                  Warning: Restoring will delete all existing data before importing the backup.
                </p>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRestorePreviewDialog(false)}
              disabled={isRestoring}
            >
              Cancel
            </Button>
            <Button
              onClick={handleExecuteRestore}
              disabled={isRestoring}
              className="gap-2"
            >
              {isRestoring ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
              Restore Backup
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Restore Result Dialog */}
      <Dialog open={showRestoreResultDialog} onOpenChange={setShowRestoreResultDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {restoreResult?.success ? (
                <CheckCircle2 className="h-5 w-5 text-success" />
              ) : (
                <XCircle className="h-5 w-5 text-destructive" />
              )}
              Restore {restoreResult?.success ? "Complete" : "Completed with Errors"}
            </DialogTitle>
          </DialogHeader>

          {restoreResult && (
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-3">
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-success">
                    {restoreResult.restored_counts.recipes || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Recipes</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-success">
                    {restoreResult.restored_counts.meals || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Meals</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-success">
                    {restoreResult.restored_counts.planner_entries || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Planner</p>
                </div>
                <div className="p-3 bg-elevated rounded-lg text-center">
                  <p className="text-xl font-bold text-success">
                    {restoreResult.restored_counts.shopping_items || 0}
                  </p>
                  <p className="text-xs text-muted-foreground">Shopping</p>
                </div>
              </div>

              {restoreResult.settings && (
                <div className="p-3 bg-elevated rounded-lg">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-success" />
                    <p className="text-sm text-foreground">App settings restored</p>
                  </div>
                </div>
              )}

              {restoreResult.errors.length > 0 && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-destructive" />
                    <p className="font-medium text-destructive">Errors</p>
                  </div>
                  <ul className="text-sm text-muted-foreground space-y-1 max-h-32 overflow-y-auto">
                    {restoreResult.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button onClick={handleCloseRestoreResultDialog}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
