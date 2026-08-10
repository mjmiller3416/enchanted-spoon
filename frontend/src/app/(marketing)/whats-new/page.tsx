import type { Metadata } from "next";
import { Badge } from "@/components/ui/badge";
import {
  CHANGELOG_ENTRIES,
  parseChangeText,
  getCategoryIcon,
  getCategoryColor,
} from "@/data/changelog";

export const metadata: Metadata = {
  title: "What's New",
  description: "New features, improvements, and fixes in Whiskful.",
};

export default function WhatsNewPage() {
  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-10 px-4 py-16 lg:px-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-page-title">What&apos;s New</h1>
        <p className="text-sm text-muted-foreground">
          New features, improvements, and fixes — newest first.
        </p>
      </header>

      {CHANGELOG_ENTRIES.map((entry, index) => {
        const Icon = getCategoryIcon(entry.title);
        return (
          <section
            key={`${entry.version}-${entry.title}-${index}`}
            className="flex flex-col gap-4"
          >
            <div className="flex flex-wrap items-center gap-3">
              <Icon className={`size-5 ${getCategoryColor(entry.title)}`} strokeWidth={1.5} />
              <h2 className="text-section-header">{entry.title}</h2>
              <Badge variant="outline">{entry.date}</Badge>
            </div>
            <ul className="flex list-disc flex-col gap-2 pl-6">
              {entry.changes.map((change) => {
                const { title, description } = parseChangeText(change);
                return (
                  <li key={change} className="leading-7 text-foreground-subtle">
                    <span className="font-medium text-foreground">{title}</span>
                    {description && <> — {description}</>}
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </article>
  );
}
