import type { Metadata } from "next";
import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { ConsentCard } from "./_components/ConsentCard";

export const metadata: Metadata = {
  title: "Connect an app",
  robots: { index: false, follow: false },
};

/**
 * OAuth consent for the ChatGPT connector (the authorization endpoint in the
 * backend's /.well-known/oauth-authorization-server). Clerk's middleware
 * protects it, so a signed-out visitor signs in first and returns here with
 * the query intact.
 */
export default function OAuthAuthorizePage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background p-4">
      {/* Suspense boundary required: ConsentCard reads useSearchParams() */}
      <Suspense
        fallback={<Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={1.5} />}
      >
        <ConsentCard />
      </Suspense>
    </main>
  );
}
