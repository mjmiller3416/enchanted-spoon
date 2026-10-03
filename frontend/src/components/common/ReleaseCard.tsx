"use client";

import { ArrowRight, Bug, ChevronDown, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import {
  describeMinorChanges,
  formatReleaseDate,
  type Release,
  type ReleaseHighlight,
} from "@/data/changelog";

interface ReleaseCardProps {
  release: Release;
  /** Marks the release as new since the user's last visit */
  isNew?: boolean;
  /** Briefly rings the card (deep-link target) */
  highlighted?: boolean;
  /**
   * Called with a highlight's href when its "Try it" button is pressed.
   * Omit to hide the buttons (e.g. on the public page, where the links would
   * bounce visitors to sign-in).
   */
  onNavigate?: (href: string) => void;
  className?: string;
}

/**
 * ReleaseCard — one release in "What's new": headline, 1–3 highlights with
 * an optional screenshot and "Try it" button, then the smaller improvements
 * and fixes tucked behind a collapsible summary. Presentational only — the
 * caller owns navigation so the card stays free of Next.js runtime imports.
 */
export function ReleaseCard({
  release,
  isNew = false,
  highlighted = false,
  onNavigate,
  className,
}: ReleaseCardProps) {
  const minorSummary = describeMinorChanges(release);

  return (
    <Card
      data-release-id={release.id}
      className={cn(
        "gap-5 p-5 transition-shadow duration-500",
        highlighted && "ring-2 ring-primary shadow-glow-primary",
        className
      )}
    >
      <header className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <time dateTime={release.id.slice(0, 10)} className="text-xs text-muted-foreground">
            {formatReleaseDate(release.id)}
          </time>
          {isNew && (
            <Badge variant="default" size="sm">
              New
            </Badge>
          )}
        </div>
        <h3 className="text-lg font-semibold leading-snug text-foreground">
          {release.headline}
        </h3>
      </header>

      <div className="flex flex-col gap-5">
        {release.highlights.map((highlight) => (
          <HighlightBlock
            key={highlight.title}
            highlight={highlight}
            onNavigate={onNavigate}
          />
        ))}
      </div>

      {minorSummary && (
        <Collapsible className="-mx-2 border-t border-border pt-3">
          <CollapsibleTrigger size="sm" className="group text-muted-foreground">
            <span>{minorSummary}</span>
            <ChevronDown
              className="size-4 transition-transform duration-200 group-data-[state=open]:rotate-180"
              strokeWidth={1.5}
            />
          </CollapsibleTrigger>
          <CollapsibleContent className="flex flex-col gap-4 px-2 pt-3">
            {release.improvements && release.improvements.length > 0 && (
              <MinorList icon={Zap} label="Improvements" items={release.improvements} />
            )}
            {release.fixes && release.fixes.length > 0 && (
              <MinorList icon={Bug} label="Fixes" items={release.fixes} />
            )}
          </CollapsibleContent>
        </Collapsible>
      )}
    </Card>
  );
}

function HighlightBlock({
  highlight,
  onNavigate,
}: {
  highlight: ReleaseHighlight;
  onNavigate?: (href: string) => void;
}) {
  const { title, body, image, href, cta } = highlight;

  return (
    <section className="flex flex-col gap-2">
      {image && (
        <div className="overflow-hidden rounded-lg border border-border bg-muted">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={image.src}
            alt={image.alt}
            loading="lazy"
            className="aspect-video w-full object-cover object-top"
          />
        </div>
      )}
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
      {href && onNavigate && (
        <Button
          variant="outline"
          size="sm"
          className="mt-1 self-start"
          onClick={() => onNavigate(href)}
        >
          {cta ?? "Try it"}
          <ArrowRight className="size-4" strokeWidth={1.5} />
        </Button>
      )}
    </section>
  );
}

function MinorList({
  icon: Icon,
  label,
  items,
}: {
  icon: typeof Zap;
  label: string;
  items: string[];
}) {
  return (
    <div className="flex flex-col gap-2">
      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        <Icon className="size-3.5" strokeWidth={1.5} />
        {label}
      </p>
      <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-foreground marker:text-muted-foreground">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
