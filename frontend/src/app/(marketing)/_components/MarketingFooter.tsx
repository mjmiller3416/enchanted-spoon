import Link from "next/link";
import { Logo } from "@/components/layout/Logo";
import { appConfig } from "@/lib/config";

export function MarketingFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 py-10 text-center sm:flex-row sm:justify-between sm:text-left lg:px-6">
        <div className="flex flex-col items-center gap-2 sm:items-start">
          <div className="flex items-center gap-2">
            <Logo className="h-6 w-6 text-primary" />
            <span className="font-semibold text-foreground">{appConfig.appName}</span>
          </div>
          <p className="text-sm text-muted-foreground">{appConfig.tagline}</p>
        </div>
        <nav
          aria-label="Footer"
          className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted-foreground"
        >
          <Link href="/pricing" className="transition-colors hover:text-foreground">
            Pricing
          </Link>
          <Link href="/privacy" className="transition-colors hover:text-foreground">
            Privacy
          </Link>
          <Link href="/terms" className="transition-colors hover:text-foreground">
            Terms
          </Link>
          <Link href="/whats-new" className="transition-colors hover:text-foreground">
            What&apos;s New
          </Link>
          <a
            href={`mailto:${appConfig.supportEmail}`}
            className="transition-colors hover:text-foreground"
          >
            Contact
          </a>
        </nav>
      </div>
    </footer>
  );
}
