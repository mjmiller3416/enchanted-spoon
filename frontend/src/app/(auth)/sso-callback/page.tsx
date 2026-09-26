"use client";

import { AuthenticateWithRedirectCallback } from "@clerk/nextjs";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export default function SSOCallbackPage() {
  return (
    <Card className="w-full max-w-md">
      <CardContent className="flex flex-col items-center gap-4 py-12" role="status">
        <Loader2 className="size-8 animate-spin text-primary" strokeWidth={1.5} />
        <p className="text-sm text-muted-foreground">Completing sign in...</p>
        <AuthenticateWithRedirectCallback signInFallbackRedirectUrl="/dashboard" signUpFallbackRedirectUrl="/dashboard" />
      </CardContent>
    </Card>
  );
}
