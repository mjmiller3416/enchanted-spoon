/**
 * Google and Apple sign-in for the native shell. The provider page opens in
 * the system browser (SFSafariViewController / Chrome Custom Tabs), not the
 * WebView. Google rejects embedded WebViews, and Apple's web flow is built
 * for Safari. Clerk redirects back to `enchantedspoon://sso-callback`, which
 * NativeRuntime loads into `/sso-callback` on the hosted origin.
 *
 * Add `enchantedspoon://sso-callback` to the Clerk dashboard's allowed
 * redirect URLs before this path can finish. Apple also needs the Services
 * ID connection in docs/SIGN_IN_WITH_APPLE.md.
 */

import type { HostedOAuthStrategy } from "@/lib/native/social-sign-in";

export const NATIVE_OAUTH_REDIRECT = "enchantedspoon://sso-callback";

interface VerificationLike {
  externalVerificationRedirectURL?: URL | string | null;
}

interface OAuthResource {
  create: (params: {
    strategy: HostedOAuthStrategy;
    redirectUrl: string;
    redirectUrlComplete?: string;
  }) => Promise<unknown>;
  firstFactorVerification?: VerificationLike;
  verifications?: { externalAccount?: VerificationLike };
}

function redirectTarget(resource: OAuthResource): string | null {
  const candidate =
    resource.firstFactorVerification?.externalVerificationRedirectURL ??
    resource.verifications?.externalAccount?.externalVerificationRedirectURL ??
    null;
  if (!candidate) return null;
  return candidate instanceof URL ? candidate.toString() : candidate;
}

const PROVIDER_LABEL: Record<HostedOAuthStrategy, string> = {
  oauth_apple: "Apple",
  oauth_google: "Google",
};

export async function startOAuthInSystemBrowser(
  resource: OAuthResource,
  strategy: HostedOAuthStrategy,
): Promise<void> {
  await resource.create({
    strategy,
    redirectUrl: NATIVE_OAUTH_REDIRECT,
    redirectUrlComplete: NATIVE_OAUTH_REDIRECT,
  });
  const url = redirectTarget(resource);
  if (!url) {
    throw new Error(
      `${PROVIDER_LABEL[strategy]} didn't return a sign-in link. Check the Clerk redirect allowlist.`,
    );
  }
  const { Browser } = await import("@capacitor/browser");
  await Browser.open({ url });
}

export async function startGoogleOAuthInSystemBrowser(resource: OAuthResource): Promise<void> {
  await startOAuthInSystemBrowser(resource, "oauth_google");
}
