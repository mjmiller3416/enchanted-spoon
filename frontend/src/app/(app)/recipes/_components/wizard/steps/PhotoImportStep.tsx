"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Images, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

export interface PhotoImportDraft {
  id: string;
  name: string;
  previewUrl: string;
}

function ImportProgress({ onCancel }: { onCancel: () => void }) {
  const [progress, setProgress] = useState(8);

  useEffect(() => {
    const started = performance.now();
    const timer = window.setInterval(() => {
      const elapsed = performance.now() - started;
      const next = Math.min(90, Math.round(8 + (1 - Math.exp(-elapsed / 8000)) * 82));
      setProgress(next);
    }, 200);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <Card role="status" aria-live="polite">
      <CardContent className="space-y-3 py-4">
        <div className="flex items-center gap-3">
          <Loader2 className="size-4 animate-spin text-primary" strokeWidth={1.5} />
          <p className="text-sm font-medium text-foreground">Reading the recipe…</p>
        </div>
        <Progress value={progress} aria-label="Import progress" />
        <p className="text-sm text-muted-foreground">
          This usually takes a few seconds. You can cancel and your photos stay here.
        </p>
        <Button type="button" variant="outline" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      </CardContent>
    </Card>
  );
}

interface PhotoImportStepProps {
  photos: PhotoImportDraft[];
  maxPhotos: number;
  isPreparing: boolean;
  isImporting: boolean;
  error: string | null;
  canRetry: boolean;
  onAddFiles: (files: File[]) => void;
  onRemove: (id: string) => void;
  onRetry: () => void;
  onCancel: () => void;
}

export function PhotoImportStep({
  photos,
  maxPhotos,
  isPreparing,
  isImporting,
  error,
  canRetry,
  onAddFiles,
  onRemove,
  onRetry,
  onCancel,
}: PhotoImportStepProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const libraryRef = useRef<HTMLInputElement>(null);
  const busy = isPreparing || isImporting;
  const full = photos.length >= maxPhotos;

  const takeFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const list = event.target.files;
    if (list && list.length > 0) onAddFiles(Array.from(list));
    event.target.value = "";
  };

  return (
    <div className="space-y-6">
      {isImporting && <ImportProgress onCancel={onCancel} />}

      {error && (
        <div role="alert" aria-live="assertive">
          <Card className="border-destructive">
            <CardContent className="space-y-3 py-3">
              <p className="text-sm text-destructive">{error}</p>
              {canRetry && photos.length > 0 && !isImporting && (
                <Button type="button" variant="outline" size="sm" onClick={onRetry}>
                  Try again
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <p className="text-sm text-muted-foreground">
        Snap a recipe card or cookbook page. You can review and edit everything before saving.
      </p>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          type="button"
          variant="outline"
          className="flex-1"
          onClick={() => cameraRef.current?.click()}
          disabled={busy || full}
        >
          <Camera strokeWidth={1.5} />
          Snap a recipe
        </Button>
        <Button
          type="button"
          variant="outline"
          className="flex-1"
          onClick={() => libraryRef.current?.click()}
          disabled={busy || full}
        >
          <Images strokeWidth={1.5} />
          Choose photos
        </Button>
      </div>
      <input
        ref={cameraRef}
        id="photo-import-camera"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={takeFiles}
        disabled={busy || full}
      />
      <input
        ref={libraryRef}
        id="photo-import-library"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={takeFiles}
        disabled={busy || full}
      />

      <p className="text-sm text-muted-foreground">
        {photos.length === 0
          ? "Up to 4 photos of the same recipe, in page order."
          : `${photos.length} of ${maxPhotos}`}
      </p>
      {isPreparing && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
          <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />
          Preparing photo…
        </p>
      )}

      {photos.length > 0 && (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {photos.map((photo, index) => (
            <li key={photo.id} className="relative aspect-square overflow-hidden rounded-md bg-muted">
              <img
                src={photo.previewUrl}
                alt={`Selected photo ${index + 1}, ${photo.name}`}
                className="h-full w-full object-contain"
              />
              <Button
                type="button"
                size="icon-sm"
                variant="secondary"
                className="absolute top-1 right-1"
                aria-label={`Remove ${photo.name}`}
                onClick={() => onRemove(photo.id)}
                disabled={busy}
              >
                <X strokeWidth={1.5} />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
