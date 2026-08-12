"use client";

import { useEffect } from "react";
import { useSignIn, useSignUp } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Logo } from "@/components/layout/Logo";

/**
 * SSO Callback page for handling OAuth redirects (e.g., Google sign-in).
 * This page completes the authentication flow after the user returns from the OAuth provider.
 */
export default function SSOCallbackPage() {
  const { signIn, setActive: setSignInActive } = useSignIn();
  const { signUp, setActive: setSignUpActive } = useSignUp();
  const router = useRouter();

  useEffect(() => {
    async function handleCallback() {
      // Check if this is a sign-in or sign-up flow
      // Use signIn.status for OAuth flows (not firstFactorVerification which is for password/OTP)
      const signInStatus = signIn?.status;
      const signUpStatus = signUp?.status;

      try {
        if (signInStatus === "complete" && signIn?.createdSessionId) {
          // Sign-in completed successfully
          await setSignInActive({ session: signIn.createdSessionId });
          router.push("/dashboard");
        } else if (signUpStatus === "complete" && signUp?.createdSessionId) {
          // Sign-up completed successfully
          await setSignUpActive({ session: signUp.createdSessionId });
          router.push("/dashboard");
        } else {
          // Still processing or needs additional steps
          // The Clerk SDK will handle the OAuth callback automatically
          // and update the signIn/signUp objects
        }
      } catch (error) {
        console.error("SSO callback error:", error);
        router.push("/sign-in");
      }
    }

    handleCallback();
  }, [signIn, signUp, setSignInActive, setSignUpActive, router]);

  return (
    <Card className="w-full max-w-md">
      <CardContent className="flex flex-col items-center justify-center py-12 space-y-4">
        <Logo className="h-12 w-auto" />
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">
          Completing sign in...
        </p>
      </CardContent>
    </Card>
  );
}
