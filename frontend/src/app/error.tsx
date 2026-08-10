"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Logo } from "@/components/layout/Logo";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center gap-6 py-12 text-center">
          <Logo className="h-12 w-auto" />
          <div className="space-y-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Something went wrong
            </h1>
            <p className="text-sm text-muted-foreground">
              An unexpected error occurred. You can try again, or head back home.
            </p>
            {error.digest && (
              <p className="text-xs text-muted-foreground">
                Error reference: {error.digest}
              </p>
            )}
          </div>
          <div className="flex items-center gap-4">
            <Button onClick={reset}>Try again</Button>
            <Button asChild variant="ghost">
              <Link href="/">Go home</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
