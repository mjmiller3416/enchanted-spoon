import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SocialAuthButtons } from "@/components/auth/SocialAuthButtons";
import {
  IOS_GOOGLE_BUTTON_CLASS,
  IOS_SOCIAL_BLOCK_CLASS,
  environmentUrl,
  googleSignInOfferedOn,
  oauthStrategyEnabled,
  socialFirstFactorMessage,
} from "@/lib/native/social-sign-in";

const productionSocial = {
  user_settings: {
    social: {
      oauth_google: {
        enabled: true,
        authenticatable: true,
        strategy: "oauth_google",
        name: "Google",
      },
    },
  },
};

describe("oauth strategy detection", () => {
  it("matches the production instance, which has Google and not Apple", () => {
    expect(oauthStrategyEnabled(productionSocial, "oauth_google")).toBe(true);
    expect(oauthStrategyEnabled(productionSocial, "oauth_apple")).toBe(false);
  });

  it("reads Clerk's in-memory environment and the strategy list", () => {
    const clerk = {
      __internal_environment: {
        userSettings: {
          authenticatableSocialStrategies: ["oauth_google", "oauth_apple"],
        },
      },
    };
    expect(oauthStrategyEnabled(clerk, "oauth_apple")).toBe(true);
    expect(oauthStrategyEnabled({ __unstable__environment: clerk.__internal_environment }, "oauth_apple")).toBe(
      true,
    );
  });

  it("ignores a provider that cannot be used to sign in", () => {
    const source = {
      userSettings: {
        social: {
          oauth_apple: { enabled: true, authenticatable: false, strategy: "oauth_apple" },
        },
      },
    };
    expect(oauthStrategyEnabled(source, "oauth_apple")).toBe(false);
  });

  it("returns null until an environment payload exists", () => {
    expect(oauthStrategyEnabled({}, "oauth_apple")).toBeNull();
    expect(oauthStrategyEnabled(null, "oauth_apple")).toBeNull();
  });
});

describe("iOS Google fallback", () => {
  it("hides Google only on iOS unless the flag is on", () => {
    expect(googleSignInOfferedOn("ios", false)).toBe(false);
    expect(googleSignInOfferedOn("ios", true)).toBe(true);
    expect(googleSignInOfferedOn("web", false)).toBe(true);
    expect(googleSignInOfferedOn("android", false)).toBe(true);
  });

  it("tells a Google-only account how to continue when the iPhone app hides Google", () => {
    const hidden = socialFirstFactorMessage(["oauth_google"], {
      appleOffered: false,
      googleOffered: false,
      supportEmail: "info@enchantedspoon.app",
    });
    expect(hidden).toContain("isn't offered in the iPhone app");
    expect(hidden).toContain("info@enchantedspoon.app");

    const shown = socialFirstFactorMessage(["oauth_google"], {
      appleOffered: false,
      googleOffered: true,
      supportEmail: "info@enchantedspoon.app",
    });
    expect(shown).toBe('This account signs in with Google. Use "Continue with Google" above.');
  });
});

describe("environment URL", () => {
  it("only accepts a hostname", () => {
    expect(environmentUrl("clerk.enchantedspoon.app")).toBe(
      "https://clerk.enchantedspoon.app/v1/environment",
    );
    expect(environmentUrl("https://clerk.enchantedspoon.app")).toBeNull();
    expect(environmentUrl("")).toBeNull();
  });
});

describe("iOS stylesheet", () => {
  it("hides Google only when the document is the iOS shell", () => {
    const css = readFileSync(resolve("src/app/globals.css"), "utf8");
    expect(css).toContain("html.native-ios .ios-social-auth");
    expect(css).toContain("html.native-ios .ios-google-sign-in");
  });
});

describe("social buttons", () => {
  it("keeps Google in the page and hides the block on iOS until Apple is enabled", () => {
    const { container } = render(
      <SocialAuthButtons
        appleEnabled={false}
        disabled={false}
        pending={null}
        onApple={() => undefined}
        onGoogle={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Continue with Apple" })).toBeNull();
    expect(container.querySelector(`.${IOS_SOCIAL_BLOCK_CLASS}`)).toBeTruthy();
  });

  it("shows Apple above Google once Clerk enables the strategy", () => {
    const { container } = render(
      <SocialAuthButtons
        appleEnabled
        disabled={false}
        pending={null}
        onApple={() => undefined}
        onGoogle={() => undefined}
      />,
    );
    const buttons = Array.from(container.querySelectorAll("button")).map((button) => button.textContent?.trim());
    expect(buttons).toEqual(["Continue with Apple", "Continue with Google"]);
    expect(container.querySelector(`.${IOS_SOCIAL_BLOCK_CLASS}`)).toBeNull();
    expect(container.querySelector(`.${IOS_GOOGLE_BUTTON_CLASS}`)).toBeTruthy();
  });
});
