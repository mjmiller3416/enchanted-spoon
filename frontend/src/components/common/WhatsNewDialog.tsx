"use client";

import { useEffect, useRef, useState } from "react";
import { Gift } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ReleaseCard } from "@/components/common/ReleaseCard";
import { RELEASES } from "@/data/changelog";

/** Releases shown before "Show earlier updates" */
const INITIAL_RELEASE_COUNT = 4;
const FOCUS_RING_MS = 2000;

interface WhatsNewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Release ids to badge as New (captured when the dialog opened) */
  unreadIds?: ReadonlySet<string>;
  /** Scroll to and briefly ring this release on open */
  focusReleaseId?: string | null;
  /** "Try it" handler — the dialog closes first, then this runs */
  onNavigate?: (href: string) => void;
}

/**
 * WhatsNewDialog — the full release history as release cards, newest first.
 * Opens on the latest few releases; older ones load on request.
 */
export function WhatsNewDialog({
  open,
  onOpenChange,
  unreadIds,
  focusReleaseId,
  onNavigate,
}: WhatsNewDialogProps) {
  const handleNavigate = onNavigate
    ? (href: string) => {
        onOpenChange(false);
        onNavigate(href);
      }
    : undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" className="flex max-h-5/6 flex-col gap-0 p-0">
        <DialogHeader className="border-b border-border px-6 pt-6 pb-4">
          <DialogTitle className="flex items-center gap-2">
            <Gift className="size-5 text-primary" strokeWidth={1.5} />
            What&apos;s new
          </DialogTitle>
          <DialogDescription>
            New features, improvements and fixes.
          </DialogDescription>
        </DialogHeader>

        {/* Content unmounts on close, so list state resets each time it opens */}
        <ReleaseList
          unreadIds={unreadIds}
          focusReleaseId={focusReleaseId}
          onNavigate={handleNavigate}
        />
      </DialogContent>
    </Dialog>
  );
}

function ReleaseList({
  unreadIds,
  focusReleaseId,
  onNavigate,
}: Pick<WhatsNewDialogProps, "unreadIds" | "focusReleaseId" | "onNavigate">) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const focusIndex = focusReleaseId
    ? RELEASES.findIndex((release) => release.id === focusReleaseId)
    : -1;
  const [showAll, setShowAll] = useState(focusIndex >= INITIAL_RELEASE_COUNT);
  const [ringedId, setRingedId] = useState<string | null>(null);

  useEffect(() => {
    if (focusIndex < 0) return;
    const releaseId = RELEASES[focusIndex].id;
    // Wait for the open animation so the scroll position sticks
    const scrollTimer = setTimeout(() => {
      const container = scrollRef.current;
      const target = container?.querySelector<HTMLElement>(
        `[data-release-id="${releaseId}"]`
      );
      if (container && target) {
        container.scrollTop = target.offsetTop - container.offsetTop - 16;
      }
      setRingedId(releaseId);
    }, 150);
    const clearTimer = setTimeout(() => setRingedId(null), 150 + FOCUS_RING_MS);
    return () => {
      clearTimeout(scrollTimer);
      clearTimeout(clearTimer);
    };
  }, [focusIndex]);

  const visible = showAll ? RELEASES : RELEASES.slice(0, INITIAL_RELEASE_COUNT);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      <div className="flex flex-col gap-4 p-4 sm:p-6">
        {visible.map((release) => (
          <ReleaseCard
            key={release.id}
            release={release}
            isNew={unreadIds?.has(release.id)}
            highlighted={ringedId === release.id}
            onNavigate={onNavigate}
          />
        ))}
        {!showAll && RELEASES.length > INITIAL_RELEASE_COUNT && (
          <Button
            variant="ghost"
            className="self-center text-muted-foreground"
            onClick={() => setShowAll(true)}
          >
            Show earlier updates
          </Button>
        )}
      </div>
    </div>
  );
}
