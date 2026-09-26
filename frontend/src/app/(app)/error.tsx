"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Error boundary for the signed-in app. Rendered inside the (app) layout, so
 * the navigation stays usable and the user can move to another section
 * instead of losing the whole app to the root boundary.
 */
export default function AppErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-1 items-center justify-center p-4 py-16">
      <Card className="w-full max-w-md">
        <CardContent className="flex flex-col items-center gap-6 py-10 text-center">
          <AlertTriangle className="size-10 text-destructive" strokeWidth={1.5} />
          <div className="space-y-2">
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              This page hit a problem
            </h1>
            <p className="text-sm text-muted-foreground">
              Your data is safe. Try again, or use the menu to go somewhere else.
            </p>
            {error.digest && (
              <p className="text-xs text-muted-foreground">Error reference: {error.digest}</p>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Button onClick={reset} className="gap-2">
              <RotateCcw className="size-4" strokeWidth={1.5} />
              Try again
            </Button>
            <Button asChild variant="ghost">
              <Link href="/dashboard">Go to Home</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
