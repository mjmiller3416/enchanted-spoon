"use client";

import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useTour } from "@/lib/providers/TourProvider";

/**
 * TourReplayCard — compact Settings entry point for replaying the
 * onboarding tour. Sits under the section nav on every breakpoint and doubles
 * as the tour's final step target.
 */
export function TourReplayCard({ className }: { className?: string }) {
  const { startTour, isActive } = useTour();

  return (
    <Card
      data-tour="settings-replay"
      className={cn(
        "flex-row items-center gap-3 p-4 lg:flex-col lg:items-stretch",
        className
      )}
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <Compass className="mt-0.5 size-5 shrink-0 text-primary" strokeWidth={1.5} />
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">App tour</p>
          <p className="text-xs text-muted-foreground">
            A one-minute walkthrough of recipes, planning, and shopping.
          </p>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={startTour}
        disabled={isActive}
        className="shrink-0"
      >
        Replay tour
      </Button>
    </Card>
  );
}
