import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/Logo";
import { appConfig } from "@/lib/config";

const textLink =
  "h-11 items-center rounded-lg px-3 text-sm font-medium text-foreground hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background";

export function MarketingHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-2 px-4 lg:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-2 rounded-lg" aria-label={`${appConfig.appName} home`}>
          <Logo className="h-8 w-auto shrink-0" />
          <span className="hidden truncate font-display text-lg text-foreground sm:inline sm:text-xl">
            {appConfig.appName}
          </span>
        </Link>
        <nav aria-label="Account" className="flex shrink-0 items-center gap-1">
          <Link href="/pricing" className={`hidden sm:inline-flex ${textLink}`}>
            Pricing
          </Link>
          <Button asChild variant="ghost" className="h-11 px-3">
            <Link href="/sign-in">Sign in</Link>
          </Button>
          <Button asChild className="h-11 px-3 sm:px-4">
            <Link href="/sign-up">Start free</Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
