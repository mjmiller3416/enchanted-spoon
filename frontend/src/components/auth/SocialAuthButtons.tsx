"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  IOS_GOOGLE_BUTTON_CLASS,
  IOS_GOOGLE_SIGN_IN_ENABLED,
  IOS_SOCIAL_BLOCK_CLASS,
} from "@/lib/native/social-sign-in";

type OAuthProvider = "apple" | "google";

type SocialAuthButtonsProps = {
  appleEnabled: boolean;
  disabled: boolean;
  pending: OAuthProvider | null;
  onApple: () => void;
  onGoogle: () => void;
};

/**
 * Apple is rendered only after Clerk reports the strategy. Google stays in
 * the markup on every platform; the iOS shell hides it with CSS until
 * NEXT_PUBLIC_IOS_GOOGLE_SIGN_IN=true, so the hosted page does not flash
 * the button before hydration.
 */
export function SocialAuthButtons({
  appleEnabled,
  disabled,
  pending,
  onApple,
  onGoogle,
}: SocialAuthButtonsProps) {
  const hideGoogleOnIos = !IOS_GOOGLE_SIGN_IN_ENABLED;

  return (
    <div
      className={cn(
        "flex flex-col gap-4",
        !appleEnabled && hideGoogleOnIos && IOS_SOCIAL_BLOCK_CLASS,
      )}
    >
      {appleEnabled && (
        <Button
          type="button"
          variant="outline"
          className="w-full gap-2"
          onClick={onApple}
          disabled={disabled}
        >
          {pending === "apple" ? (
            <Loader2 className="size-5 animate-spin" strokeWidth={1.5} />
          ) : (
            <AppleIcon />
          )}
          Continue with Apple
        </Button>
      )}

      <div className={hideGoogleOnIos ? IOS_GOOGLE_BUTTON_CLASS : undefined}>
        <Button
          type="button"
          variant="outline"
          className="w-full gap-2"
          onClick={onGoogle}
          disabled={disabled}
        >
          {pending === "google" ? (
            <Loader2 className="size-5 animate-spin" strokeWidth={1.5} />
          ) : (
            <GoogleIcon />
          )}
          Continue with Google
        </Button>
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-card px-2 text-muted-foreground">or</span>
        </div>
      </div>
    </div>
  );
}

function AppleIcon() {
  return (
    <svg className="size-5" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M16.37 12.72c.02 2.14 1.88 2.85 1.9 2.86-.02.05-.3 1.02-.98 2.02-.59.87-1.21 1.73-2.18 1.75-.95.02-1.26-.56-2.35-.56s-1.43.54-2.33.58c-.93.04-1.64-.94-2.24-1.8-1.22-1.76-2.15-4.97-.9-7.14.62-1.08 1.73-1.76 2.94-1.78.92-.02 1.78.62 2.35.62.56 0 1.62-.76 2.73-.65.46.02 1.77.19 2.61 1.42-.07.04-1.56.91-1.55 2.68ZM14.9 6.3c.5-.6.83-1.44.74-2.28-.72.03-1.58.48-2.1 1.08-.46.53-.86 1.38-.75 2.19.8.06 1.62-.4 2.11-.99Z"
      />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg className="size-5" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}
