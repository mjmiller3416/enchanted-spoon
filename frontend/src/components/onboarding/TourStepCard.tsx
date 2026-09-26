"use client";

import type { ElementType, ReactNode } from "react";
import { ArrowLeft, ArrowRight, Check, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface TourStepCardProps {
  /** Step heading */
  title: string;
  /** Short explanation of the highlighted feature */
  description: ReactNode;
  /** Optional lucide icon shown in a tinted chip beside the title */
  icon?: ElementType;
  /** 1-based position of this step */
  stepNumber: number;
  /** Total number of steps */
  stepCount: number;
  /** Advance to the next step (or finish on the last step) */
  onNext: () => void;
  /** Go back one step; the Back button is hidden on the first step */
  onBack?: () => void;
  /** End the tour early */
  onSkip: () => void;
  /** Override the primary button label (defaults to "Next" / "Finish") */
  nextLabel?: string;
  /** Shows a spinner on Next and disables navigation (e.g. while a page loads) */
  isPending?: boolean;
  /** id applied to the title, for the dialog's aria-labelledby */
  titleId?: string;
  /** id applied to the description, for the dialog's aria-describedby */
  descriptionId?: string;
  className?: string;
}

/**
 * TourStepCard — the floating card for one step of the guided tour.
 *
 * Purely presentational: renders the step title/body, a "Step N of M"
 * counter with progress dots, and Back / Next (Finish) / Skip controls, all
 * driven by props. The Next button carries `data-tour-autofocus` so a host
 * dialog can move focus to it when the step appears.
 */
export function TourStepCard({
  title,
  description,
  icon: Icon,
  stepNumber,
  stepCount,
  onNext,
  onBack,
  onSkip,
  nextLabel,
  isPending = false,
  titleId,
  descriptionId,
  className,
}: TourStepCardProps) {
  const isFirst = stepNumber <= 1;
  const isLast = stepNumber >= stepCount;
  const primaryLabel = nextLabel ?? (isLast ? "Finish" : "Next");

  return (
    <Card className={cn("gap-4 p-5 shadow-floating", className)}>
      {/* Counter + skip */}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium text-muted-foreground tabular-nums">
          Step {stepNumber} of {stepCount}
        </p>
        <Button
          variant="ghost"
          size="xs"
          onClick={onSkip}
          className="text-muted-foreground hover:text-foreground"
        >
          Skip tour
        </Button>
      </div>

      {/* Title + body */}
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="size-5" strokeWidth={1.5} aria-hidden="true" />
          </div>
        )}
        <div className="flex min-w-0 flex-col gap-1">
          <h2 id={titleId} className="text-base font-semibold text-foreground">
            {title}
          </h2>
          <p id={descriptionId} className="text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        </div>
      </div>

      {/* Progress + navigation */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ol className="flex items-center gap-1.5" aria-hidden="true">
          {Array.from({ length: stepCount }, (_, index) => (
            <li
              key={index}
              className={cn(
                "h-1.5 rounded-full transition-all duration-300 motion-reduce:transition-none",
                index === stepNumber - 1
                  ? "w-4 bg-primary"
                  : index < stepNumber - 1
                    ? "w-1.5 bg-primary/40"
                    : "w-1.5 bg-border"
              )}
            />
          ))}
        </ol>

        <div className="ml-auto flex items-center gap-2">
          {!isFirst && onBack && (
            <Button variant="outline" size="sm" onClick={onBack} disabled={isPending}>
              <ArrowLeft className="size-4" strokeWidth={1.5} />
              Back
            </Button>
          )}
          <Button size="sm" onClick={onNext} disabled={isPending} data-tour-autofocus>
            {isPending ? (
              <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />
            ) : isLast ? (
              <Check className="size-4" strokeWidth={1.5} />
            ) : null}
            {primaryLabel}
            {!isPending && !isLast && (
              <ArrowRight className="size-4" strokeWidth={1.5} />
            )}
          </Button>
        </div>
      </div>
    </Card>
  );
}
