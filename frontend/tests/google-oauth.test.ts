import { beforeEach, describe, expect, it, vi } from "vitest";
import { NATIVE_OAUTH_REDIRECT, startOAuthInSystemBrowser } from "@/lib/native/google-oauth";

const browser = vi.hoisted(() => ({ open: vi.fn() }));

vi.mock("@capacitor/browser", () => ({
  Browser: { open: browser.open },
}));

const GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth?client_id=test";

beforeEach(() => {
  browser.open.mockReset();
  browser.open.mockResolvedValue(undefined);
});

describe("native Google OAuth", () => {
  it("starts sign-in with strategy and redirectUrl, then opens the provider URL", async () => {
    const create = vi.fn(async () => undefined);
    const resource = {
      create,
      firstFactorVerification: {
        externalVerificationRedirectURL: new URL(GOOGLE_URL),
      },
    };

    await startOAuthInSystemBrowser(resource, "oauth_google");

    expect(create).toHaveBeenCalledTimes(1);
    const params = create.mock.calls[0][0] as Record<string, unknown>;
    expect(params).toEqual({
      strategy: "oauth_google",
      redirectUrl: NATIVE_OAUTH_REDIRECT,
    });
    expect(params).not.toHaveProperty("redirectUrlComplete");
    expect(browser.open).toHaveBeenCalledWith({ url: GOOGLE_URL });
  });

  it("starts a Google sign-up the same way and opens the external-account URL", async () => {
    const create = vi.fn(async () => undefined);
    const resource = {
      create,
      verifications: {
        externalAccount: {
          externalVerificationRedirectURL: GOOGLE_URL,
        },
      },
    };

    await startOAuthInSystemBrowser(resource, "oauth_google");

    expect(create).toHaveBeenCalledTimes(1);
    const params = create.mock.calls[0][0] as Record<string, unknown>;
    expect(params).toEqual({
      strategy: "oauth_google",
      redirectUrl: NATIVE_OAUTH_REDIRECT,
    });
    expect(params).not.toHaveProperty("redirectUrlComplete");
    expect(browser.open).toHaveBeenCalledWith({ url: GOOGLE_URL });
  });
});
