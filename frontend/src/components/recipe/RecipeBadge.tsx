"use client";

import { Globe, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { RecipeGroupResponseDTO } from "@/types/recipe";

type BadgeType = "category" | "mealType" | "dietary" | "group" | "ai" | "difficulty" | "imported" | "sample";
type BadgeSize = "sm" | "md" | "lg";
type BadgeVariant = "overlay" | "inline" | "outline";

interface RecipeBadgeProps {
  label: string;
  type: BadgeType;
  size?: BadgeSize;
  variant?: BadgeVariant;
  className?: string;
  groups?: RecipeGroupResponseDTO[]; // Only used when type="group"
}

/**
 * RecipeBadge - Reusable badge component for recipe metadata
 *
 * Renders on the shadcn Badge primitive (variant="plain") with type-specific
 * colors from semantic theme tokens.
 *
 * @param label - Text to display in badge
 * @param type - Badge type determines color scheme
 *   - "category": Teal/primary color (e.g., "Pasta", "Seafood")
 *   - "mealType": Purple/secondary color (e.g., "Dinner", "Lunch")
 *   - "dietary": Gray/accent color (e.g., "Vegetarian", "Pescatarian")
 *   - "group": Muted color for recipe groups
 *   - "ai": Chart-6 for AI-generated recipes
 *   - "imported": Chart-5 for recipes imported from a website
 *   - "sample": Muted color for onboarding starter-pack recipes
 * @param size - Badge size: sm, md, lg
 * @param variant - "overlay" for floating on images, "inline" for content areas, "outline" for bordered style
 * @param className - Additional classes
 * @param groups - Array of RecipeGroupResponseDTO (only used when type="group")
 */
export function RecipeBadge({
  label,
  type,
  size = "md",
  variant = "inline",
  className,
  groups = [],
}: RecipeBadgeProps) {
  // Type-specific color schemes (semantic theme tokens)
  const typeColors = {
    category: "bg-primary text-primary-foreground",
    mealType: "bg-secondary/90 text-secondary-foreground",
    dietary: "bg-accent text-accent-foreground",
    group: "bg-accent text-accent-foreground",
    ai: "bg-chart-6 text-primary-foreground",
    difficulty: "bg-chart-4 text-primary-foreground",
    imported: "bg-chart-5 text-primary-foreground",
    sample: "bg-muted text-muted-foreground",
  };

  // Outline variant uses border + text color instead of filled background
  const outlineTypeColors = {
    category: "bg-transparent border-2 border-primary text-primary",
    mealType: "bg-transparent border-2 border-secondary text-secondary",
    dietary: "bg-transparent border-2 border-accent text-accent-foreground",
    group: "bg-transparent border-2 border-accent text-accent",
    ai: "bg-transparent border-2 border-chart-6 text-chart-6",
    difficulty: "bg-transparent border-2 border-chart-4 text-chart-4",
    imported: "bg-transparent border-2 border-chart-5 text-chart-5",
    sample: "bg-transparent border-2 border-border text-muted-foreground",
  };

  // Size variants
  const sizeClasses = {
    sm: "px-3 py-1 text-xs",
    md: "px-4 py-1.5 text-sm",
    lg: "px-4 py-2 text-sm",
  };

  // Variant-specific styles
  const variantClasses = {
    overlay: "backdrop-blur-md shadow-elevated",
    inline: "",
    outline: "",
  };

  const badgeClasses = cn(
    "rounded-full",

    // Type colors (outline variant uses border instead of background)
    variant === "outline" ? outlineTypeColors[type] : typeColors[type],

    // Size
    sizeClasses[size],

    // Variant
    variantClasses[variant],

    // Custom classes
    className
  );

  // For group badges with multiple groups, show count with tooltip
  if (type === "group" && groups.length > 0) {
    const primaryGroupName = groups[0].name;
    const additionalCount = groups.length - 1;

    const badgeContent = (
      <Badge
        variant="plain"
        size={null}
        className={cn(
          badgeClasses,
          "relative",
          // Add right margin when count badge is present to prevent overlap
          additionalCount > 0 && "mr-3"
        )}
      >
        {primaryGroupName.toLowerCase()}
        {additionalCount > 0 && (
          <Badge
            variant="plain"
            size={null}
            className={cn(
              "absolute -top-2 -right-2 rounded-full p-0",
              "bg-primary text-primary-foreground border-2 border-card",
              size === "sm" ? "size-5 text-xs" : "size-6 text-xs"
            )}
          >
            +{additionalCount}
          </Badge>
        )}
      </Badge>
    );

    // If multiple groups, wrap in tooltip
    if (additionalCount > 0) {
      return (
        <Tooltip>
          <TooltipTrigger asChild>{badgeContent}</TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              {groups.map((group) => (
                <div key={group.id} className="text-sm">
                  {group.name}
                </div>
              ))}
            </div>
          </TooltipContent>
        </Tooltip>
      );
    }

    return badgeContent;
  }

  // Standard badge rendering for non-group types
  return (
    <Badge variant="plain" size={null} className={badgeClasses}>
      {type === "ai" && <Sparkles strokeWidth={1.5} />}
      {type === "imported" && <Globe strokeWidth={1.5} />}
      {type === "group" ? label.toLowerCase() : label}
    </Badge>
  );
}

/**
 * RecipeBadgeGroup - Wrapper for multiple badges
 * Handles spacing and wrapping
 */
interface RecipeBadgeGroupProps {
  children: React.ReactNode;
  className?: string;
}

export function RecipeBadgeGroup({ children, className }: RecipeBadgeGroupProps) {
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {children}
    </div>
  );
}
