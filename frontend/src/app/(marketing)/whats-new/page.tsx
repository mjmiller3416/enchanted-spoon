import type { Metadata } from "next";
import { ReleaseCard } from "@/components/common/ReleaseCard";
import { RELEASES } from "@/data/changelog";
import { appConfig } from "@/lib/config";

export const metadata: Metadata = {
  title: "What's New",
  description: `New features, improvements, and fixes in ${appConfig.appName}.`,
};

export default function WhatsNewPage() {
  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-16 lg:px-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-page-title">What&apos;s New</h1>
        <p className="text-sm text-muted-foreground">
          New features, improvements, and fixes — newest first.
        </p>
      </header>

      {RELEASES.map((release) => (
        <ReleaseCard key={release.id} release={release} />
      ))}
    </article>
  );
}
