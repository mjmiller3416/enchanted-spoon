"use client";

import { cn } from "@/lib/utils";
import { getHeroBannerUrl } from "@/lib/imageUtils";
import { RecipeImage } from "@/components/recipe/RecipeImage";

interface RecipeHeroImageProps {
  /** Primary source: banner_image_path (21:9) */
  bannerSrc: string | null | undefined;
  /** Fallback source: reference_image_path (1:1) - will be cropped */
  fallbackSrc?: string | null | undefined;
  alt: string;
  className?: string;
  children?: React.ReactNode;
}

/**
 * RecipeHeroImage - Hero image for recipe detail pages
 *
 * Features:
 * - Native 21:9 aspect ratio (matches generated banner images)
 * - Max height capped at 500px for very wide screens
 * - Gradient overlay for text readability
 * - Children slot for overlay elements (back button, favorite button, etc.)
 */
export function RecipeHeroImage({
  bannerSrc,
  fallbackSrc,
  alt,
  className,
  children,
}: RecipeHeroImageProps) {
  // Transform Cloudinary URLs to use smart crop for banner dimensions
  // This applies AI-powered subject detection to avoid cropping out the dish
  // Prefer banner image, fallback to reference image
  const effectiveSrc = getHeroBannerUrl(bannerSrc || fallbackSrc);
  const hasImage = bannerSrc || fallbackSrc;

  return (
    <div
      className={cn(
        "relative w-full bg-elevated overflow-hidden",
        hasImage ? "h-64 sm:h-80" : "h-28",
        className
      )}
    >
      {hasImage && <RecipeImage
        src={effectiveSrc}
        alt={alt}
        fill
        loading="eager"
        sizes="100vw"
        iconSize="xl"
        showLoadingState={false}
        className="w-full h-full object-cover"
      />}

      {/* Gradient overlay - only shown when image is present */}
      {hasImage && (
        <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent" />
      )}

      {/* Overlay content (back button, favorite, etc.) */}
      {children}
    </div>
  );
}
