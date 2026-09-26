"use client";

import type { ElementType, ReactNode } from "react";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface TourWelcomeHighlight {
  icon: ElementType;
  label: string;
}

export interface TourWelcomeCardProps {
  /** Heading, e.g. "Welcome to Enchanted Spoon" */
  title: string;
  /** One or two sentences on what the tour covers */
  description: ReactNode;
  /** Optional brand mark or illustration rendered above the title */
  media?: ReactNode;
  /** Optional feature highlights shown as a compact icon list */
  highlights?: TourWelcomeHighlight[];
  /** Primary action label (defaults to "Show me around") */
  startLabel?: string;
  /** Secondary action label (defaults to "Skip for now") */
  skipLabel?: string;
  /** Approximate tour length shown under the actions, e.g. "About a minute" */
  durationHint?: string;
  onStart: () => void;
  onSkip: () => void;
  /** id applied to the title, for the dialog's aria-labelledby */
  titleId?: string;
  /** id applied to the description, for the dialog's aria-describedby */
  descriptionId?: string;
  className?: string;
}

/**
 * TourWelcomeCard — the intro card shown before the first tour step.
 *
 * Purely presentational: a centered welcome with optional brand media and
 * feature highlights, plus Start / Skip actions. The start button carries
 * `data-tour-autofocus` so a host dialog can focus it on open.
 */
export function TourWelcomeCard({
  title,
  description,
  media,
  highlights,
  startLabel = "Show me around",
  skipLabel = "Skip for now",
  durationHint,
  onStart,
  onSkip,
  titleId,
  descriptionId,
  className,
}: TourWelcomeCardProps) {
  return (
    <Card className={cn("items-center gap-5 p-6 text-center shadow-floating", className)}>
      {media && <div className="flex justify-center">{media}</div>}

      <div className="flex flex-col gap-2">
        <h2 id={titleId} className="text-xl font-semibold text-foreground text-balance">
          {title}
        </h2>
        <p id={descriptionId} className="text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>

      {highlights && highlights.length > 0 && (
        <ul className="flex w-full flex-wrap justify-center gap-2">
          {highlights.map(({ icon: Icon, label }) => (
            <li
              key={label}
              className="flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
            >
              <Icon className="size-3.5" strokeWidth={1.5} aria-hidden="true" />
              {label}
            </li>
          ))}
        </ul>
      )}

      <div className="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-center">
        <Button variant="ghost" onClick={onSkip}>
          {skipLabel}
        </Button>
        <Button onClick={onStart} data-tour-autofocus>
          {startLabel}
          <ArrowRight className="size-4" strokeWidth={1.5} />
        </Button>
      </div>

      {durationHint && (
        <p className="text-xs text-muted-foreground">{durationHint}</p>
      )}
    </Card>
  );
}
