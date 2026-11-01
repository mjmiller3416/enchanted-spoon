import { describe, expect, it } from "vitest";
import { extractSharedRecipeUrl, importUrlFromDeepLink, isOAuthCallback } from "@/lib/native/share-link";

describe("shared recipe links", () => {
  it("pulls a TikTok URL out of share-sheet text", () => {
    expect(extractSharedRecipeUrl("Check this https://www.tiktok.com/@cook/video/1")).toBe(
      "https://www.tiktok.com/@cook/video/1",
    );
  });

  it("reads the import deep link", () => {
    const href = "enchantedspoon://import?url=" + encodeURIComponent("https://www.instagram.com/reel/abc");
    expect(importUrlFromDeepLink(href)).toBe("https://www.instagram.com/reel/abc");
  });

  it("ignores the OAuth callback", () => {
    expect(importUrlFromDeepLink("enchantedspoon://sso-callback?rotating_token_nonce=1")).toBeNull();
    expect(isOAuthCallback("enchantedspoon://sso-callback?rotating_token_nonce=1")).toBe(true);
  });
});
