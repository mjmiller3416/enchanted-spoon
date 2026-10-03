"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useSpotlight } from "@/lib/providers/WhatsNewProvider";
import type { SpotlightId } from "@/data/changelog";

interface NewFeatureBadgeProps {
  spotlight: SpotlightId;
  className?: string;
}

/**
 * NewFeatureBadge — a small "New" pill beside a recently released feature.
 * Shows for 30 days after the release that spotlights it, only to accounts
 * that existed before it, until the feature calls `useSpotlight(id).dismiss`.
 */
export function NewFeatureBadge({ spotlight, className }: NewFeatureBadgeProps) {
  const { active } = useSpotlight(spotlight);
  if (!active) return null;

  return (
    <Badge variant="default" size="sm" className={cn("normal-case tracking-normal", className)}>
      New
    </Badge>
  );
}
