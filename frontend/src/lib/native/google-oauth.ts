/**
 * Google sign-in for the native shell. The OAuth page opens in the system
 * browser (SFSafariViewController / Chrome Custom Tabs), not the WebView,
 * because Google rejects embedded WebViews. Clerk redirects back to
 * `enchantedspoon://sso-callback`, which NativeRuntime loads into
 * `/sso-callback` on the hosted origin.
 *
 * Add `enchantedspoon://sso-callback` to the Clerk dashboard's allowed
 * redirect URLs before this path can finish.
 */

export const NATIVE_OAUTH_REDIRECT = "enchantedspoon://sso-callback";

interface VerificationLike {
  externalVerificationRedirectURL?: URL | string | null;
}

interface OAuthResource {
  create: (params: {
    strategy: "oauth_google";
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

export async function startGoogleOAuthInSystemBrowser(resource: OAuthResource): Promise<void> {
  await resource.create({
    strategy: "oauth_google",
    redirectUrl: NATIVE_OAUTH_REDIRECT,
    redirectUrlComplete: NATIVE_OAUTH_REDIRECT,
  });
  const url = redirectTarget(resource);
  if (!url) {
    throw new Error("Google didn't return a sign-in link. Check the Clerk redirect allowlist.");
  }
  const { Browser } = await import("@capacitor/browser");
  await Browser.open({ url });
}
