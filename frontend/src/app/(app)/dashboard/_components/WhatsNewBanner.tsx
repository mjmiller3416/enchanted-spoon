"use client";

import { Gift, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useTour } from "@/lib/providers/TourProvider";
import { useWhatsNew } from "@/lib/providers/WhatsNewProvider";
import { RELEASES } from "@/data/changelog";

/**
 * WhatsNewBanner — Home's nudge after a release the user hasn't seen: the
 * latest headline and highlight thumbnail, opening the dialog at that
 * release. Dismissing it (or viewing the release anywhere) marks it seen.
 */
export function WhatsNewBanner({ className }: { className?: string }) {
  const { hasNew, unreadIds, openWhatsNew, markSeen } = useWhatsNew();
  const { isActive: tourActive } = useTour();

  const latest = RELEASES[0];
  if (!hasNew || tourActive || !latest) return null;

  const image = latest.highlights.find((highlight) => highlight.image)?.image;
  const highlightTitles = latest.highlights.map((highlight) => highlight.title).join(" · ");
  const moreCount = Math.max(0, unreadIds.size - 1);

  return (
    <Card className={cn("flex-row items-center gap-4 p-4 shadow-raised", className)}>
      {image ? (
        <div className="hidden h-16 w-28 shrink-0 overflow-hidden rounded-lg border border-border bg-muted sm:block">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image.src} alt="" className="size-full object-cover object-top" />
        </div>
      ) : (
        <div className="hidden size-12 shrink-0 items-center justify-center rounded-lg bg-primary/10 sm:flex">
          <Gift className="size-6 text-primary" strokeWidth={1.5} />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 text-xs font-medium text-primary">
          <Gift className="size-3.5 sm:hidden" strokeWidth={1.5} />
          What&apos;s new
        </p>
        <p className="text-sm font-medium text-foreground">{latest.headline}</p>
        <p className="line-clamp-1 text-xs text-muted-foreground">
          {highlightTitles}
          {moreCount > 0 && ` · and ${moreCount} more update${moreCount === 1 ? "" : "s"}`}
        </p>
      </div>

      <Button
        size="sm"
        variant="outline"
        className="shrink-0"
        aria-label="See what's new"
        onClick={() => openWhatsNew(latest.id)}
      >
        <span className="sm:hidden">View</span>
        <span className="hidden sm:inline">See what&apos;s new</span>
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={markSeen}
        aria-label="Dismiss what's new"
        className="size-8 shrink-0 text-muted-foreground"
      >
        <X className="size-4" strokeWidth={1.5} />
      </Button>
    </Card>
  );
}
