import Link from "next/link";
import { Logo } from "@/components/layout/Logo";
import { appConfig } from "@/lib/config";

const footerLink =
  "inline-flex min-h-11 items-center rounded-md px-1 text-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

export function MarketingFooter() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-start sm:justify-between lg:px-6">
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <Logo className="h-6 w-auto" />
            <span className="font-display text-lg text-foreground">{appConfig.appName}</span>
          </div>
          <p className="max-w-xs text-sm text-muted-foreground">{appConfig.tagline}</p>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap items-center gap-x-4 gap-y-1">
          <Link href="/pricing" className={footerLink}>
            Pricing
          </Link>
          <Link href="/privacy" className={footerLink}>
            Privacy
          </Link>
          <Link href="/terms" className={footerLink}>
            Terms
          </Link>
          <Link href="/delete-account" className={footerLink}>
            Delete account
          </Link>
          <Link href="/whats-new" className={footerLink}>
            What&apos;s New
          </Link>
          <a href={`mailto:${appConfig.supportEmail}`} className={footerLink}>
            Contact
          </a>
        </nav>
      </div>
    </footer>
  );
}
