"use client";

import { useState } from "react";
import { useSignUp } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import {
  AuthLogo,
  authCardContentClassName,
  authCardHeaderClassName,
  authCardTitleClassName,
} from "@/components/auth/AuthScreen";
import { SocialAuthButtons } from "@/components/auth/SocialAuthButtons";
import { appConfig } from "@/lib/config";
import { getPostAuthRedirect } from "@/lib/authRedirect";
import { useAppleSignInOffered } from "@/hooks/useAppleSignInOffered";
import { startOAuthInSystemBrowser } from "@/lib/native/google-oauth";
import { isNativeApp } from "@/lib/native/platform";
import type { HostedOAuthStrategy } from "@/lib/native/social-sign-in";

type SignUpStep = "details" | "verification";
type OAuthProvider = "apple" | "google";

const OAUTH_STRATEGY: Record<OAuthProvider, HostedOAuthStrategy> = {
  apple: "oauth_apple",
  google: "oauth_google",
};

export function SignUpForm() {
  const { isLoaded, signUp, setActive } = useSignUp();
  const appleOffered = useAppleSignInOffered();
  const router = useRouter();

  const [step, setStep] = useState<SignUpStep>("details");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [oauthPending, setOauthPending] = useState<OAuthProvider | null>(null);

  const handleOAuth = async (provider: OAuthProvider) => {
    if (!isLoaded || !signUp || isLoading) return;
    const strategy = OAUTH_STRATEGY[provider];
    const label = provider === "apple" ? "Apple" : "Google";
    setError("");
    setIsLoading(true);
    setOauthPending(provider);

    try {
      if (isNativeApp()) {
        await startOAuthInSystemBrowser(signUp, strategy);
        return;
      }
      await signUp.authenticateWithRedirect({
        strategy,
        redirectUrl: "/sso-callback",
        redirectUrlComplete: getPostAuthRedirect(),
      });
    } catch (err) {
      setError(`Failed to start ${label} sign-up. Please try again.`);
      console.error(`${label} sign-up error:`, err);
      setIsLoading(false);
      setOauthPending(null);
    }
  };

  // Handle registration form submission
  const handleSignUpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded || !signUp) return;

    setError("");
    setIsLoading(true);

    try {
      // Create the sign-up
      await signUp.create({
        emailAddress: email,
        password,
      });

      // Send verification email
      await signUp.prepareEmailAddressVerification({
        strategy: "email_code",
      });

      setStep("verification");
    } catch (err: unknown) {
      const clerkError = err as { errors?: Array<{ message: string; code?: string }> };
      const errorMessage = clerkError.errors?.[0]?.message || "Failed to create account";
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle verification code submission
  const handleVerificationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded || !signUp) return;

    setError("");
    setIsLoading(true);

    try {
      const result = await signUp.attemptEmailAddressVerification({
        code,
      });

      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
        router.push(getPostAuthRedirect());
      } else {
        // e.g. missing_requirements: a field Clerk requires that this form doesn't collect
        setError(
          "Your email is verified, but your account needs one more step we can't finish here. " +
            `Please contact ${appConfig.supportEmail}.`
        );
      }
    } catch (err: unknown) {
      const clerkError = err as { errors?: Array<{ message: string }> };
      setError(clerkError.errors?.[0]?.message || "Invalid verification code");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle OTP code change - auto-submit when complete
  const handleCodeChange = (value: string) => {
    setCode(value);
    // Auto-submit when all 6 digits are entered
    if (value.length === 6 && !isLoading) {
      handleVerificationSubmit({ preventDefault: () => {} } as React.FormEvent);
    }
  };

  // Resend verification code
  const handleResendCode = async () => {
    if (!isLoaded || !signUp) return;

    setError("");
    setIsLoading(true);

    try {
      await signUp.prepareEmailAddressVerification({
        strategy: "email_code",
      });
      setCode("");
    } catch (err: unknown) {
      const clerkError = err as { errors?: Array<{ message: string }> };
      setError(clerkError.errors?.[0]?.message || "Failed to resend code");
    } finally {
      setIsLoading(false);
    }
  };

  // Go back to details step
  const handleBack = () => {
    setStep("details");
    setCode("");
    setError("");
  };

  if (!isLoaded) {
    return (
      <Card className="w-full max-w-md">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className={authCardHeaderClassName}>
        <AuthLogo />
        <div className="space-y-2 [@media(max-height:500px)]:space-y-1">
          <CardTitle className={authCardTitleClassName}>
            {step === "details" ? "Create your account" : "Verify your email"}
          </CardTitle>
          <CardDescription>
            {step === "details" && `Welcome to ${appConfig.appName}! Let's get started`}
            {step === "verification" && `Enter the code sent to ${email}`}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className={authCardContentClassName}>
        {/* Error display */}
        {error && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg">
            {error}
          </div>
        )}

        {step === "details" && (
          <>
            <SocialAuthButtons
              appleEnabled={appleOffered}
              disabled={isLoading}
              pending={oauthPending}
              onApple={() => void handleOAuth("apple")}
              onGoogle={() => void handleOAuth("google")}
            />

            {/* Registration Form */}
            <form onSubmit={handleSignUpSubmit} className="space-y-4 [@media(max-height:500px)]:space-y-2">
              <div className="space-y-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  autoComplete="email"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Create a password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  autoComplete="new-password"
                  required
                  minLength={8}
                />
                <p className="text-xs text-muted-foreground [@media(max-height:500px)]:hidden">
                  Must be at least 8 characters
                </p>
              </div>
              <Button
                type="submit"
                className="w-full gap-2"
                disabled={isLoading || !email || !password}
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                Create account
              </Button>
            </form>
          </>
        )}

        {step === "verification" && (
          <form onSubmit={handleVerificationSubmit} className="space-y-6">
            <div className="space-y-4">
              <Label className="text-center block">Verification code</Label>
              <div className="flex justify-center">
                <InputOTP
                  maxLength={6}
                  value={code}
                  onChange={handleCodeChange}
                  disabled={isLoading}
                >
                  <InputOTPGroup>
                    <InputOTPSlot index={0} />
                    <InputOTPSlot index={1} />
                    <InputOTPSlot index={2} />
                    <InputOTPSlot index={3} />
                    <InputOTPSlot index={4} />
                    <InputOTPSlot index={5} />
                  </InputOTPGroup>
                </InputOTP>
              </div>
            </div>
            <Button
              type="submit"
              className="w-full gap-2"
              disabled={isLoading || code.length !== 6}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              Verify email
            </Button>
            <div className="flex flex-col gap-2">
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={handleResendCode}
                disabled={isLoading}
              >
                Resend code
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={handleBack}
                disabled={isLoading}
              >
                Back
              </Button>
            </div>
          </form>
        )}

        {/* Sign in link */}
        <p className="text-center text-sm text-muted-foreground pt-2">
          Already have an account?{" "}
          <Link href="/sign-in" className="text-primary hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
