"use client";

import { Lightbulb } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";

/** Trailing sentence punctuation stays outside the link href. */
const TRAILING_PUNCTUATION = /[.,;:!?)]+$/;

const WRAP_CLASSES = "break-words [overflow-wrap:anywhere]";

/**
 * Split note text into plain strings and anchor elements.
 * Only http(s) URLs become links. The text is rendered as React nodes,
 * never as HTML.
 */
function linkifyNotes(notes: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let key = 0;

  for (const match of notes.matchAll(/https?:\/\/[^\s<>"']+/gi)) {
    const start = match.index ?? 0;
    const raw = match[0];
    if (start > cursor) {
      nodes.push(notes.slice(cursor, start));
    }

    const url = raw.replace(TRAILING_PUNCTUATION, "");
    const suffix = raw.slice(url.length);
    if (url) {
      nodes.push(
        <a
          key={key}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className={`${WRAP_CLASSES} underline`}
        >
          {url}
        </a>,
      );
      key += 1;
    } else {
      nodes.push(raw);
    }
    if (suffix) {
      nodes.push(suffix);
    }
    cursor = start + raw.length;
  }

  if (cursor < notes.length) {
    nodes.push(notes.slice(cursor));
  }
  return nodes;
}

interface ChefNotesCardProps {
  notes: string | null | undefined;
}

/**
 * Chef's Notes on the recipe page. The text column can shrink beside the
 * icon, and long words or URLs wrap inside the card padding.
 */
export function ChefNotesCard({ notes }: ChefNotesCardProps) {
  if (!notes) return null;

  return (
    <Card className="mt-8 min-w-0 border-warning/30 bg-warning/5 print:mt-4 print:border print:border-gray-300 print:bg-gray-50 print:shadow-none">
      <CardContent className="p-6 print:p-4">
        <div className="flex min-w-0 items-start gap-4 print:gap-2">
          <div className="flex-shrink-0 rounded-lg bg-warning/20 p-2 print:hidden">
            <Lightbulb className="h-5 w-5 text-warning" strokeWidth={1.5} aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="mb-2 text-lg font-bold text-foreground print:mb-1 print:text-base print:text-black">
              Chef&apos;s Notes
            </h3>
            <p className={`leading-relaxed text-foreground/80 print:text-sm print:text-black ${WRAP_CLASSES}`}>
              {linkifyNotes(notes)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
