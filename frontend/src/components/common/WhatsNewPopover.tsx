"use client";

import { useState } from "react";
import { Gift } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { RELEASES, formatReleaseDate } from "@/data/changelog";

const POPOVER_RELEASE_COUNT = 3;

interface WhatsNewPopoverProps {
  /** Release ids still unread when the page loaded */
  unreadIds: ReadonlySet<string>;
  /** Show the dot on the trigger */
  hasNewUpdates: boolean;
  /** Fired when the popover opens — the caller marks releases as seen */
  onOpen: () => void;
  onViewAll: () => void;
  onViewRelease: (releaseId: string) => void;
}

/**
 * WhatsNewPopover — top-bar entry point to "What's new": the latest few
 * releases as headline rows, each opening the full dialog at that release.
 */
export function WhatsNewPopover({
  unreadIds,
  hasNewUpdates,
  onOpen,
  onViewAll,
  onViewRelease,
}: WhatsNewPopoverProps) {
  const [open, setOpen] = useState(false);
  const recent = RELEASES.slice(0, POPOVER_RELEASE_COUNT);
  const unreadCount = recent.filter((release) => unreadIds.has(release.id)).length;

  const handleSelect = (releaseId: string) => {
    setOpen(false);
    onViewRelease(releaseId);
  };

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) onOpen();
      }}
    >
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={hasNewUpdates ? "What's new (new updates)" : "What's new"}
          className="relative"
        >
          <Gift className="size-5" strokeWidth={1.5} />
          {hasNewUpdates && (
            <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-primary animate-pulse" />
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent align="end" sideOffset={8} className="w-96 p-0">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-sm font-semibold text-foreground">What&apos;s new</span>
          {unreadCount > 0 && (
            <Badge variant="default" size="sm">
              {unreadCount} new
            </Badge>
          )}
        </div>

        <ul>
          {recent.map((release, idx) => {
            const isUnread = unreadIds.has(release.id);
            return (
              <li key={release.id}>
                <Button
                  variant="ghost"
                  onClick={() => handleSelect(release.id)}
                  className={cn(
                    "flex h-auto w-full flex-col items-stretch gap-1 rounded-none px-4 py-3 text-left whitespace-normal",
                    idx < recent.length - 1 && "border-b border-border"
                  )}
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-xs font-normal text-muted-foreground">
                      {formatReleaseDate(release.id)}
                    </span>
                    {isUnread && (
                      <span className="size-2 shrink-0 rounded-full bg-primary" aria-label="New" />
                    )}
                  </span>
                  <span className="text-sm font-medium leading-snug text-foreground">
                    {release.headline}
                  </span>
                  <span className="line-clamp-1 text-xs font-normal text-muted-foreground">
                    {release.highlights.map((highlight) => highlight.title).join(" · ")}
                  </span>
                </Button>
              </li>
            );
          })}
        </ul>

        <div className="border-t border-border">
          <Button
            variant="ghost"
            className="h-12 w-full rounded-none rounded-b-lg text-primary hover:text-primary"
            onClick={() => {
              setOpen(false);
              onViewAll();
            }}
          >
            See all updates
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
