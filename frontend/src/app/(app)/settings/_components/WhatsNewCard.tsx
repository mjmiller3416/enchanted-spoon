"use client";

import { Gift } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useWhatsNew } from "@/lib/providers/WhatsNewProvider";

/**
 * WhatsNewCard — Settings entry point to the release notes, under the tour
 * card. The only way into "What's new" besides the top bar and More menu.
 */
export function WhatsNewCard({ className }: { className?: string }) {
  const { hasNew, openWhatsNew } = useWhatsNew();

  return (
    <Card
      className={cn(
        "flex-row items-center gap-3 p-4 lg:flex-col lg:items-stretch",
        className
      )}
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <Gift className="mt-0.5 size-5 shrink-0 text-primary" strokeWidth={1.5} />
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-sm font-medium text-foreground">
            What&apos;s new
            {hasNew && (
              <Badge variant="default" size="sm">
                New
              </Badge>
            )}
          </p>
          <p className="text-xs text-muted-foreground">
            Recent features, improvements and fixes.
          </p>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => openWhatsNew()}
        className="shrink-0"
      >
        See updates
      </Button>
    </Card>
  );
}
