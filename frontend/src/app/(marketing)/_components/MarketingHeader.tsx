import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/Logo";
import { appConfig } from "@/lib/config";

/**
 * Slimmed-down cousin of the in-app TopNav: same height, logo, and name
 * placement so signing in feels like the chrome "filled in," not switched.
 */
export function MarketingHeader() {
  return (
    <header className="sticky top-0 z-30 h-16 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-4 lg:px-6">
        <Link href="/" className="flex items-center gap-3" aria-label="Meal Genie home">
          <Logo className="h-8 w-8 shrink-0 text-primary" />
          <span className="whitespace-nowrap text-lg font-semibold text-foreground">
            {appConfig.appName}
          </span>
        </Link>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" className="hidden sm:inline-flex">
            <Link href="/pricing">Pricing</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link href="/sign-in">Sign in</Link>
          </Button>
          <Button asChild>
            <Link href="/sign-up">Get started</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
