"use client";

import { Heart, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FavoriteButtonProps {
  isFavorite: boolean;
  onToggle: (e: React.MouseEvent) => void;
  variant?: "overlay" | "inline";
  size?: "sm" | "md" | "lg";
  readOnly?: boolean;
  pending?: boolean;
  className?: string;
}

/**
 * FavoriteButton - Reusable favorite toggle button with animations
 *
 * @param isFavorite - Whether item is favorited
 * @param onToggle - Click handler (must call e.stopPropagation() internally)
 * @param variant - "overlay" for floating on images, "inline" for content areas
 * @param size - Button size: sm (small cards), md (medium cards), lg (large cards)
 * @param readOnly - When true, displays state without interaction (indicator mode)
 * @param className - Additional classes
 */
export function FavoriteButton({
  isFavorite,
  onToggle,
  variant = "overlay",
  size = "md",
  readOnly = false,
  pending = false,
  className,
}: FavoriteButtonProps) {
  // Size variants for the button
  const sizeClasses = {
    sm: "p-2",
    md: "p-3",
    lg: "p-2",
  };

  // Size variants for the heart icon
  const iconSizes = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-6 w-6",
  };

  // Variant-specific styles
  const variantClasses = {
    overlay: cn(
      "rounded-full backdrop-blur-md shadow-lg",
      "bg-background/70 hover:bg-background/90"
    ),
    inline: cn(
      "rounded-lg",
      "hover:bg-elevated"
    ),
  };

  // Read-only mode: render as a non-interactive indicator
  if (readOnly) {
    return (
      <div
        className={cn(
          // Base styles
          "flex-shrink-0",

          // Color - always show the favorited state
          isFavorite ? "text-destructive" : "text-muted-foreground",

          // Size
          sizeClasses[size],

          // Custom classes
          className
        )}
        aria-label={isFavorite ? "Favorited" : "Not favorited"}
      >
        <Heart
          strokeWidth={1.5}
          className={cn(
            iconSizes[size],
            isFavorite && "fill-current"
          )}
        />
      </div>
    );
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      disabled={pending}
      aria-busy={pending}
      aria-pressed={isFavorite}
      onClick={onToggle}
      className={cn(
        // Base styles
        "transition-all duration-200 flex-shrink-0",

        // Hover scale effect
        "hover:scale-110 active:scale-95",

        // Focus states for keyboard accessibility
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background",

        // Color states
        isFavorite
          ? "text-destructive"
          : "text-muted-foreground hover:text-destructive",

        // Size
        sizeClasses[size],

        // Variant
        variantClasses[variant],

        // Custom classes
        className
      )}
      aria-label={isFavorite ? "Remove from favorites" : "Add to favorites"}
    >
      {pending ? <Loader2 className="size-5 animate-spin" strokeWidth={1.5} /> : <Heart
        strokeWidth={1.5}
        className={cn(
          // Icon size
          iconSizes[size],
          
          // Transition
          "transition-all duration-200",
          
          // Fill when favorited
          isFavorite && "fill-current",
          
          // Pulse animation on favorite
          isFavorite && "animate-pulse-once"
        )}
      />}
    </Button>
  );
}
