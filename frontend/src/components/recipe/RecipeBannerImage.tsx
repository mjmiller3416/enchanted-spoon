"use client";

import { cn } from "@/lib/utils";
import { getHeroBannerUrl } from "@/lib/imageUtils";
import { RecipeImage } from "./RecipeImage";

interface RecipeBannerImageProps {
  /** Primary source: banner_image_path (21:9) */
  bannerSrc: string | null | undefined;
  /** Fallback source: reference_image_path (1:1) - will be cropped */
  fallbackSrc?: string | null | undefined;
  alt: string;
  className?: string;
  /** Display aspect ratio */
  aspectRatio?: "16/9" | "21/9" | "3/1";
  showLoadingState?: boolean;
}

/**
 * RecipeBannerImage - Wide image display for banners and landscape contexts
 *
 * Uses banner_image_path (21:9) as primary source with fallback to
 * reference_image_path (1:1, cropped via Cloudinary g_auto).
 *
 * Wraps RecipeImage for consistent error handling and placeholder display.
 */
export function RecipeBannerImage({
  bannerSrc,
  fallbackSrc,
  alt,
  className,
  aspectRatio = "16/9",
  showLoadingState = false,
}: RecipeBannerImageProps) {
  // Determine which source to use and apply appropriate transformation
  const effectiveSrc = getHeroBannerUrl(bannerSrc || fallbackSrc);

  const aspectClasses = {
    "16/9": "aspect-[16/9]",
    "21/9": "aspect-[21/9]",
    "3/1": "aspect-[3/1]",
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden bg-elevated",
        aspectClasses[aspectRatio],
        className
      )}
    >
      <RecipeImage
        src={effectiveSrc}
        alt={alt}
        fill
        iconSize="lg"
        showLoadingState={showLoadingState}
        className="object-cover"
      />
    </div>
  );
}
