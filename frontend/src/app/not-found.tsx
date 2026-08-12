import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/Logo";

export default function NotFound() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-6 bg-background p-4 text-center">
      <Logo className="h-12 w-auto" />
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Page not found
        </h1>
        <p className="text-muted-foreground">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
      </div>
      <div className="flex items-center gap-4">
        <Button asChild>
          <Link href="/">Go home</Link>
        </Button>
        <Button asChild variant="ghost">
          <Link href="/recipes">Browse recipes</Link>
        </Button>
      </div>
    </main>
  );
}
