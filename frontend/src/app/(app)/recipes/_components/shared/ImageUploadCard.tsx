"use client";

import { memo, useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  Upload,
  ImageIcon,
  Sparkles,
  RefreshCw,
  Check,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { getErrorMessage } from "@/lib/utils";
import { useSettings } from "@/hooks/persistence/useSettings";
import { useGenerateImage } from "@/hooks/api/useAI";

type ImageState = "empty" | "uploading" | "uploaded" | "generating" | "generated" | "error";

interface ImageUploadCardProps {
  /** Current image preview URL (data URL or Cloudinary URL) */
  imagePreview: string | null;
  /** Handler for file upload input changes */
  onImageUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Handler when user accepts a generated image (reference + optional banner) */
  onGeneratedImageAccept: (
    referenceBase64: string,
    referenceDataUrl: string,
    bannerBase64?: string
  ) => void;
  /** Handler when user accepts a banner-only generated image */
  onBannerOnlyAccept?: (bannerBase64: string) => void;
  /** Recipe name used for generating the image prompt */
  recipeName: string;
  /** Whether the current image was AI-generated */
  isAiGenerated?: boolean;
  /** Handler to update the AI-generated flag */
  onAiGeneratedChange?: (isAiGenerated: boolean) => void;
  /** Whether in edit mode (enables selective generation UI) */
  isEditMode?: boolean;
  /** Compact layout — no Card wrapper, 1:1 drop zone (for wizard) */
  compact?: boolean;
}

export const ImageUploadCard = memo(function ImageUploadCard({
  imagePreview,
  onImageUpload,
  onGeneratedImageAccept,
  recipeName,
  isAiGenerated = false,
  onAiGeneratedChange,
  compact = false,
}: ImageUploadCardProps) {
  const { settings } = useSettings();
  const generateImageMutation = useGenerateImage();

  // Determine initial state based on props
  const getInitialState = (): ImageState => {
    if (imagePreview) {
      return isAiGenerated ? "generated" : "uploaded";
    }
    return "empty";
  };

  const [imageState, setImageState] = useState<ImageState>(getInitialState);
  const [generatingError, setGeneratingError] = useState<string | null>(null);
  const [pendingGeneratedImage, setPendingGeneratedImage] = useState<{
    base64: string;
    dataUrl: string;
  } | null>(null);
  const [progress, setProgress] = useState(0);

  const isGenerating = imageState === "generating";

  // Update state when imagePreview changes externally
  useEffect(() => {
    if (imagePreview && imageState === "empty") {
      setImageState(isAiGenerated ? "generated" : "uploaded");
    } else if (!imagePreview && imageState !== "generating" && imageState !== "error") {
      setImageState("empty");
    }
  }, [imagePreview, isAiGenerated, imageState]);

  // Animate progress while the single photo request is in flight.
  useEffect(() => {
    if (imageState !== "generating") {
      setProgress(0);
      return;
    }
    const duration = 15000;
    const intervalMs = 100;
    const increment = (100 / duration) * intervalMs;
    const interval = setInterval(() => {
      setProgress((prev) => Math.min(prev + increment, 98));
    }, intervalMs);
    return () => clearInterval(interval);
  }, [imageState]);

  const handleGenerate = async () => {
    if (!recipeName.trim()) {
      setGeneratingError("Please enter a recipe name first");
      setImageState("error");
      return;
    }

    setImageState("generating");
    setGeneratingError(null);
    setPendingGeneratedImage(null);

    try {
      const refResult = await generateImageMutation.mutateAsync({
        recipeName,
        customPrompt: settings.aiFeatures.imageGenerationPrompt,
        imageType: "reference",
      });
      if (!refResult.success || !refResult.reference_image_data) {
        throw new Error(refResult.error || "Failed to generate photo");
      }
      setProgress(100);
      const dataUrl = `data:image/png;base64,${refResult.reference_image_data}`;
      onGeneratedImageAccept(refResult.reference_image_data, dataUrl);
      onAiGeneratedChange?.(true);
      setImageState("generated");
    } catch (error) {
      setGeneratingError(getErrorMessage(error, "Image generation failed"));
      setImageState("error");
    }
  };

  const handleAcceptGenerated = () => {
    if (pendingGeneratedImage) {
      onGeneratedImageAccept(
        pendingGeneratedImage.base64,
        pendingGeneratedImage.dataUrl
      );
      onAiGeneratedChange?.(true);
      setPendingGeneratedImage(null);
    }
  };

  const handleUploadClick = () => {
    document.getElementById("recipe-image")?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onImageUpload(e);
    setImageState("uploaded");
    onAiGeneratedChange?.(false);
    setPendingGeneratedImage(null);
    setGeneratingError(null);
  };

  // Get the image to display
  const displayImage = pendingGeneratedImage?.dataUrl || imagePreview;

  // ── Shared inner content (used by both compact and card modes) ──────────
  const innerContent = (
    <>
      {/* Header */}
      <div className={cn("flex items-center gap-2.5", compact ? "mb-3" : "mb-6")}>
        <div className={cn(
          "flex items-center justify-center rounded-lg bg-primary-surface",
          compact ? "size-7" : "size-9"
        )}>
          <ImageIcon className={cn(compact ? "size-3.5" : "size-5", "text-primary")} strokeWidth={1.5} />
        </div>
        <div>
          <h2 className={cn(compact ? "text-sm" : "text-lg", "font-semibold text-foreground leading-tight")}>
            Recipe Image
          </h2>
          <p className={cn("text-muted-foreground leading-tight", compact ? "text-xs" : "text-sm")}>
            Upload or generate
          </p>
        </div>
      </div>

      {/* Image Preview Area — always 1:1 */}
      <div className={cn(
        "w-full aspect-square rounded-xl overflow-hidden border-2 border-dashed relative",
        "transition-colors",
        imageState === "empty"
          ? "border-muted-foreground/40 bg-muted/50"
          : "border-transparent bg-muted/30"
      )}>
        {/* Empty State */}
        {imageState === "empty" && (
          <button
            type="button"
            onClick={handleUploadClick}
            className="flex flex-col items-center justify-center size-full text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <div className="size-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
              <ImageIcon className="size-6 text-muted-foreground" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium">No image uploaded</p>
            <p className="text-xs mt-0.5 text-muted-foreground">Click or drag to upload</p>
          </button>
        )}

        {/* Generating State */}
        {imageState === "generating" && (
          <div className="flex flex-col items-center justify-center size-full text-muted-foreground px-6">
            <div className="size-12 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
              <Sparkles className="size-6 text-primary animate-pulse" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-primary">Generating photo...</p>
            {/* Progress Bar */}
            <div className="w-full max-w-40 mt-4">
              <Progress value={progress} className="h-1.5" />
              <p className="text-xs mt-1.5 text-center text-muted-foreground">
                {Math.round(progress)}%
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {imageState === "error" && (
          <div className="flex flex-col items-center justify-center size-full text-muted-foreground p-4">
            <div className="size-12 rounded-xl bg-destructive/10 flex items-center justify-center mb-3">
              <AlertCircle className="size-6 text-destructive" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-destructive text-center">
              {generatingError || "Something went wrong"}
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleGenerate}
              className="mt-3"
            >
              <RefreshCw className="size-4 mr-2" strokeWidth={1.5} />
              Try Again
            </Button>
          </div>
        )}

        {/* Image Display (Generated or Uploaded) */}
        {(imageState === "generated" || imageState === "uploaded") &&
          displayImage && (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element -- src may be a base64 data URL from AI generation */}
              <img
                src={displayImage}
                alt="Recipe preview"
                className="size-full object-cover"
              />
              {/* AI Generated Badge */}
              {(imageState === "generated" || isAiGenerated) && (
                <Badge
                  className="absolute top-2.5 left-2.5 bg-primary hover:bg-primary-hover text-primary-foreground gap-1"
                >
                  <Sparkles className="size-3" strokeWidth={1.5} />
                  AI Generated
                </Badge>
              )}
            </>
          )}
      </div>

      {/* Action Buttons */}
      <div className="mt-3 space-y-2">
        {/* Empty State Buttons */}
        {imageState === "empty" && (
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size={compact ? "sm" : "default"}
              className="flex-1 gap-2"
              onClick={handleUploadClick}
            >
              <Upload className="size-4" strokeWidth={1.5} />
              Upload
            </Button>
            <Button
              type="button"
              size={compact ? "sm" : "default"}
              className="flex-1 gap-2"
              onClick={handleGenerate}
              disabled={isGenerating}
            >
              <Sparkles className="size-4" strokeWidth={1.5} />
              Generate photo
            </Button>
          </div>
        )}

        {/* Generating State */}
        {imageState === "generating" && (
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size={compact ? "sm" : "default"}
              className="flex-1 gap-2"
              onClick={handleUploadClick}
            >
              <Upload className="size-4" strokeWidth={1.5} />
              Upload
            </Button>
            <Button
              type="button"
              size={compact ? "sm" : "default"}
              className="flex-1 gap-2"
              disabled
            >
              <Sparkles className="size-4 animate-pulse" strokeWidth={1.5} />
              Generate photo
            </Button>
          </div>
        )}

        {/* Generated State (pending acceptance) */}
        {imageState === "generated" && pendingGeneratedImage && (
          <>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="default"
                size={compact ? "sm" : "default"}
                className="flex-1 gap-2"
                onClick={handleAcceptGenerated}
              >
                <Check className="size-4" strokeWidth={1.5} />
                Use This Image
              </Button>
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={handleGenerate}
                disabled={isGenerating}
                aria-label="Generate a new image"
              >
                <RefreshCw className="size-4" strokeWidth={1.5} />
              </Button>
            </div>
            <Button
              type="button"
              variant="ghost"
              size={compact ? "sm" : "default"}
              className="w-full gap-2"
              onClick={handleUploadClick}
            >
              <Upload className="size-4" strokeWidth={1.5} />
              Upload Different Image
            </Button>
          </>
        )}

        {/* Uploaded State or Accepted Generated State */}
        {((imageState === "uploaded") ||
          (imageState === "generated" && !pendingGeneratedImage && imagePreview)) && (
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size={compact ? "sm" : "default"}
                className="flex-1 gap-2"
                onClick={handleUploadClick}
              >
                <Upload className="size-4" strokeWidth={1.5} />
                Replace
              </Button>
              <Button
                type="button"
                size={compact ? "sm" : "default"}
                className="flex-1 gap-2"
                onClick={handleGenerate}
                disabled={isGenerating}
              >
                <Sparkles className="size-4" strokeWidth={1.5} />
                Regenerate photo
              </Button>
            </div>
          )}
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        id="recipe-image"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Helper text (non-compact mode only) */}
      {!compact && (
        <p className="text-xs text-muted-foreground text-center mt-3">
          AI generates one square photo. Wide banners are cropped from it.
        </p>
      )}
    </>
  );

  // ── Render: compact mode = bare div, full mode = Card wrapper ──────────

  if (compact) {
    return <div>{innerContent}</div>;
  }

  return (
    <Card>
      <CardContent className="pt-6">
        {innerContent}
      </CardContent>
    </Card>
  );
});