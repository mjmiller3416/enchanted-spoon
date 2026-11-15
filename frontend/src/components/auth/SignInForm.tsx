"use client";

import { useState } from "react";
import { useSignIn } from "@clerk/nextjs";
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
import { isNativeApp, nativePlatform } from "@/lib/native/platform";
import {
  googleSignInOfferedOn,
  socialFirstFactorMessage,
  type HostedOAuthStrategy,
} from "@/lib/native/social-sign-in";

type SignInStep =
  | "email"
  | "password"
  | "verification"
  | "reset_code"
  | "new_password"
  | "second_factor";

type SecondFactorStrategy = "totp" | "phone_code" | "email_code" | "backup_code";

type ClerkErrorShape = { errors?: Array<{ longMessage?: string; message?: string }> };

function clerkMessage(err: unknown, fallback: string): string {
  const first = (err as ClerkErrorShape)?.errors?.[0];
  return first?.longMessage || first?.message || fallback;
}

// SignInResource from useSignIn(); typed loosely to cover every status we branch on
type SignInAttempt = NonNullable<ReturnType<typeof useSignIn>["signIn"]>;

type OAuthProvider = "apple" | "google";

const OAUTH_STRATEGY: Record<OAuthProvider, HostedOAuthStrategy> = {
  apple: "oauth_apple",
  google: "oauth_google",
};

export function SignInForm() {
  const { isLoaded, signIn, setActive } = useSignIn();
  const appleOffered = useAppleSignInOffered();
  const router = useRouter();

  const [step, setStep] = useState<SignInStep>("email");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [secondFactor, setSecondFactor] = useState<SecondFactorStrategy | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [oauthPending, setOauthPending] = useState<OAuthProvider | null>(null);

  /**
   * Route any sign-in result to its next step. Every status Clerk can return
   * lands somewhere visible — nothing silently stops the spinner.
   */
  const continueSignIn = async (result: SignInAttempt) => {
    if (!setActive) return;
    switch (result.status) {
      case "complete":
        await setActive({ session: result.createdSessionId });
        router.push(getPostAuthRedirect());
        return;
      case "needs_new_password":
        setPassword("");
        setStep("new_password");
        return;
      case "needs_second_factor": {
        const factors = result.supportedSecondFactors ?? [];
        const pick = (["totp", "phone_code", "email_code", "backup_code"] as const).find((s) =>
          factors.some((f) => f.strategy === s)
        );
        if (!pick) break;
        if (pick === "phone_code" || pick === "email_code") {
          await result.prepareSecondFactor({ strategy: pick } as Parameters<
            SignInAttempt["prepareSecondFactor"]
          >[0]);
        }
        setSecondFactor(pick);
        setCode("");
        setStep("second_factor");
        return;
      }
    }
    setError(
      "This account needs a sign-in step this page doesn't support yet. " +
        `Please contact ${appConfig.supportEmail} for help.`
    );
  };

  const handleOAuth = async (provider: OAuthProvider) => {
    if (!isLoaded || !signIn || isLoading) return;
    const strategy = OAUTH_STRATEGY[provider];
    const label = provider === "apple" ? "Apple" : "Google";
    setError("");
    setIsLoading(true);
    setOauthPending(provider);

    try {
      if (isNativeApp()) {
        await startOAuthInSystemBrowser(signIn, strategy);
        return;
      }
      await signIn.authenticateWithRedirect({
        strategy,
        redirectUrl: "/sso-callback",
        redirectUrlComplete: getPostAuthRedirect(),
      });
    } catch (err) {
      setError(clerkMessage(err, `Failed to start ${label} sign-in. Please try again.`));
      console.error(`${label} sign-in error:`, err);
      setIsLoading(false);
      setOauthPending(null);
    }
  };

  // Handle email submission - determines if password or verification is needed
  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded || !signIn) return;

    setError("");
    setNotice("");
    setIsLoading(true);

    try {
      // Start the sign-in process with the email
      const result = await signIn.create({
        identifier: email,
      });

      if (result.status !== "needs_first_factor") {
        await continueSignIn(result);
        return;
      }

      const factors = result.supportedFirstFactors ?? [];
      if (factors.some((factor) => factor.strategy === "password")) {
        setStep("password");
        return;
      }

      const emailFactor = factors.find((factor) => factor.strategy === "email_code");
      if (emailFactor && "emailAddressId" in emailFactor) {
        await signIn.prepareFirstFactor({
          strategy: "email_code",
          emailAddressId: emailFactor.emailAddressId,
        });
        setStep("verification");
        return;
      }

      const socialMessage = socialFirstFactorMessage(
        factors.map((factor) => factor.strategy),
        {
          appleOffered,
          googleOffered: googleSignInOfferedOn(nativePlatform()),
          supportEmail: appConfig.supportEmail,
        },
      );
      if (socialMessage) {
        setError(socialMessage);
        return;
      }

      setError(
        `We couldn't find a way to sign in to this account. Please contact ${appConfig.supportEmail}.`
      );
    } catch (err: unknown) {
      setError(clerkMessage(err, "Invalid email address"));
    } finally {
      setIsLoading(false);
    }
  };

  // Handle password submission
  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded || !signIn) return;

    setError("");
    setIsLoading(true);

    try {
      const result = await signIn.attemptFirstFactor({
        strategy: "password",
        password,
      });
      await continueSignIn(result);
    } catch (err: unknown) {
      setError(clerkMessage(err, "Invalid password"));
    } finally {
      setIsLoading(false);
    }
  };

  // Handle verification code submission
  const handleCodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded || !signIn) return;

    setError("");
    setIsLoading(true);

    try {
      const result = await signIn.attemptFirstFactor({
        strategy: "email_code",
        code,
      });
      await continueSignIn(result);
    } catch (err: unknown) {
      setError(clerkMessage(err, "Invalid verification code"));
    } finally {
      setIsLoading(false);
    }
  };

  // Forgot password: email a reset code
  const handleForgotPassword = async () => {
    if (!isLoaded || !signIn) return;

    setError("");
    setIsLoading(true);

    try {
      await signIn.create({ strategy: "reset_password_email_code", identifier: email });
      setCode("");
      setPassword("");
      setNotice(`We sent a password reset code to ${email}.`);
      setStep("reset_code");
    } catch (err: unknown) {
      setError(clerkMessage(err, "Couldn't send a reset code. Please try again."));
    } finally {
      setIsLoading(false);
    }
  };

  // Reset code + new password
  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded || !signIn) return;

    setError("");
    setIsLoading(true);

    try {
      if (step === "reset_code") {
        const result = await signIn.attemptFirstFactor({
          strategy: "reset_password_email_code",
          code,
        });
        setNotice("");
        await continueSignIn(result);
      } else {
        const result = await signIn.resetPassword({ password, signOutOfOtherSessions: true });
        await continueSignIn(result);
      }
    } catch (err: unknown) {
      setError(clerkMessage(err, step === "reset_code" ? "Invalid reset code" : "Couldn't set that password"));
    } finally {
      setIsLoading(false);
    }
  };

  // Two-factor code
  const handleSecondFactorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded || !signIn || !secondFactor) return;

    setError("");
    setIsLoading(true);

    try {
      const result = await signIn.attemptSecondFactor({ strategy: secondFactor, code: code.trim() });
      await continueSignIn(result);
    } catch (err: unknown) {
      setError(clerkMessage(err, "Invalid code"));
    } finally {
      setIsLoading(false);
    }
  };

  // Go back to email step
  const handleBack = () => {
    setStep("email");
    setPassword("");
    setCode("");
    setError("");
    setNotice("");
    setSecondFactor(null);
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
          <CardTitle className={authCardTitleClassName}>Sign in to {appConfig.appName}</CardTitle>
          <CardDescription>
            {step === "email" && "Welcome back! Please sign in to continue"}
            {step === "password" && `Enter your password for ${email}`}
            {step === "verification" && `Enter the code sent to ${email}`}
            {step === "reset_code" && `Enter the reset code sent to ${email}`}
            {step === "new_password" && "Choose a new password"}
            {step === "second_factor" &&
              (secondFactor === "totp"
                ? "Enter the code from your authenticator app"
                : secondFactor === "backup_code"
                  ? "Enter one of your backup codes"
                  : "Enter the code we just sent you")}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className={authCardContentClassName}>
        {notice && !error && (
          <div className="p-3 text-sm text-foreground bg-muted border border-border rounded-lg" role="status">
            {notice}
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg">
            {error}
          </div>
        )}

        {step === "email" && (
          <>
            <SocialAuthButtons
              appleEnabled={appleOffered}
              disabled={isLoading}
              pending={oauthPending}
              onApple={() => void handleOAuth("apple")}
              onGoogle={() => void handleOAuth("google")}
            />

            {/* Email Form */}
            <form onSubmit={handleEmailSubmit} className="space-y-4">
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
              <Button
                type="submit"
                className="w-full gap-2"
                disabled={isLoading || !email}
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                Continue
              </Button>
            </form>
          </>
        )}

        {step === "password" && (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                autoComplete="current-password"
                autoFocus
                required
              />
            </div>
            <Button
              type="submit"
              className="w-full gap-2"
              disabled={isLoading || !password}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              Sign in
            </Button>
            <Button
              type="button"
              variant="link"
              className="w-full"
              onClick={handleForgotPassword}
              disabled={isLoading}
            >
              Forgot password?
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
          </form>
        )}

        {step === "verification" && (
          <form onSubmit={handleCodeSubmit} className="space-y-6">
            <div className="space-y-4">
              <Label className="text-center block">Verification code</Label>
              <div className="flex justify-center">
                <InputOTP
                  maxLength={6}
                  value={code}
                  onChange={setCode}
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
              Verify
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
          </form>
        )}

        {(step === "reset_code" || step === "new_password") && (
          <form onSubmit={handleResetSubmit} className="space-y-4">
            {step === "reset_code" ? (
              <div className="space-y-2">
                <Label htmlFor="reset-code">Reset code</Label>
                <Input
                  id="reset-code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  disabled={isLoading}
                  autoFocus
                  required
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="new-password">New password</Label>
                <Input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  autoFocus
                  required
                />
              </div>
            )}
            <Button
              type="submit"
              className="w-full gap-2"
              disabled={isLoading || (step === "reset_code" ? !code.trim() : !password)}
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {step === "reset_code" ? "Continue" : "Set password and sign in"}
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={handleBack} disabled={isLoading}>
              Back
            </Button>
          </form>
        )}

        {step === "second_factor" && (
          <form onSubmit={handleSecondFactorSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="second-factor-code">
                {secondFactor === "backup_code" ? "Backup code" : "Verification code"}
              </Label>
              <Input
                id="second-factor-code"
                inputMode={secondFactor === "backup_code" ? "text" : "numeric"}
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                disabled={isLoading}
                autoFocus
                required
              />
            </div>
            <Button type="submit" className="w-full gap-2" disabled={isLoading || !code.trim()}>
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              Verify
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={handleBack} disabled={isLoading}>
              Back
            </Button>
          </form>
        )}

        {/* Sign up link */}
        <p className="text-center text-sm text-muted-foreground pt-2">
          Don&apos;t have an account?{" "}
          <Link href="/sign-up" className="text-primary hover:underline font-medium">
            Sign up
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
