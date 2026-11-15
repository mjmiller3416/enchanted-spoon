/**
 * Sign in with Apple for App Store guideline 4.8.
 *
 * The production Clerk instance will not enable Apple until someone with
 * Apple Developer access creates a Services ID and a Sign in with Apple key
 * and saves them in the Clerk dashboard. The app never sees those secrets.
 * See docs/SIGN_IN_WITH_APPLE.md.
 *
 * Until that connection is on, the iOS shell hides Google so the app is not
 * offering a third-party login without an equivalent option. Web and Android
 * are unchanged. Set NEXT_PUBLIC_IOS_GOOGLE_SIGN_IN=true and redeploy the
 * hosted site only after Continue with Apple completes on a real iPhone.
 */

import type { NativePlatform } from "@/lib/native/platform";

export type HostedOAuthStrategy = "oauth_apple" | "oauth_google";

/** Baked into the hosted bundle. Anything other than "true" keeps Google off on iOS. */
export const IOS_GOOGLE_SIGN_IN_ENABLED = process.env.NEXT_PUBLIC_IOS_GOOGLE_SIGN_IN === "true";

/** Hides the whole social block on iOS when Apple is not offered yet. */
export const IOS_SOCIAL_BLOCK_CLASS = "ios-social-auth";

/** Hides Google on iOS while leaving Continue with Apple visible. */
export const IOS_GOOGLE_BUTTON_CLASS = "ios-google-sign-in";

export function googleSignInOfferedOn(
  platform: NativePlatform,
  iosGoogleEnabled: boolean = IOS_GOOGLE_SIGN_IN_ENABLED,
): boolean {
  if (platform !== "ios") return true;
  return iosGoogleEnabled;
}

type SocialProvider = {
  enabled?: boolean;
  authenticatable?: boolean;
  strategy?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") return null;
  return value as Record<string, unknown>;
}

function providerMatches(entry: unknown, strategy: HostedOAuthStrategy): boolean {
  const provider = asRecord(entry) as SocialProvider | null;
  if (!provider || provider.enabled !== true) return false;
  if (provider.authenticatable === false) return false;
  // A map entry keyed by strategy may omit the strategy field.
  return provider.strategy === undefined || provider.strategy === strategy;
}

/**
 * Whether Clerk currently allows this OAuth strategy.
 * Returns null when the Clerk environment is not on the object yet, so the
 * caller can fall back to the public Frontend API environment payload.
 * Accepts either the Clerk client (`__internal_environment` /
 * `__unstable__environment`) or the raw `/v1/environment` JSON.
 */
export function oauthStrategyEnabled(source: unknown, strategy: HostedOAuthStrategy): boolean | null {
  const root = asRecord(source);
  if (!root) return null;

  const env = asRecord(root.__internal_environment) ?? asRecord(root.__unstable__environment) ?? root;
  const settings = asRecord(env.userSettings) ?? asRecord(env.user_settings);
  if (!settings) return null;

  const listed = settings.authenticatableSocialStrategies;
  if (Array.isArray(listed)) {
    return listed.includes(strategy);
  }

  const social = settings.social;
  if (!social || typeof social !== "object") return null;

  if (Array.isArray(social)) {
    return social.some((entry) => {
      const provider = asRecord(entry);
      return provider?.strategy === strategy && providerMatches(entry, strategy);
    });
  }

  const socialRecord = asRecord(social);
  if (!socialRecord) return null;
  if (Object.prototype.hasOwnProperty.call(socialRecord, strategy)) {
    return providerMatches(socialRecord[strategy], strategy);
  }
  return Object.values(socialRecord).some(
    (entry) => asRecord(entry)?.strategy === strategy && providerMatches(entry, strategy),
  );
}

/** The loaded Clerk instance on `window`, which carries `__internal_environment`. */
export function readBrowserClerk(): unknown {
  if (typeof window === "undefined") return undefined;
  return (window as { Clerk?: unknown }).Clerk;
}

export function environmentUrl(frontendApi: string | null | undefined): string | null {
  if (!frontendApi || !/^[a-z0-9.-]+$/i.test(frontendApi)) return null;
  return `https://${frontendApi}/v1/environment`;
}

export function socialFirstFactorMessage(
  strategies: readonly string[],
  options: { appleOffered: boolean; googleOffered: boolean; supportEmail: string },
): string | null {
  if (strategies.includes("oauth_apple") && options.appleOffered) {
    return 'This account signs in with Apple. Use "Continue with Apple" above.';
  }
  if (strategies.includes("oauth_google") && options.googleOffered) {
    return 'This account signs in with Google. Use "Continue with Google" above.';
  }
  if (strategies.includes("oauth_google")) {
    return `This account signs in with Google, which isn't offered in the iPhone app. Open enchantedspoon.app in Safari, or email ${options.supportEmail}.`;
  }
  if (strategies.includes("oauth_apple")) {
    return `This account signs in with Apple. Open enchantedspoon.app in Safari, or email ${options.supportEmail}.`;
  }
  return null;
}
