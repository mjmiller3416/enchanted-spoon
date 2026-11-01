import { describe, expect, it } from "vitest";
import {
  appleStorefrontAllowsWebFoundingLink,
  mayMentionWebFoundingOffer,
} from "@/lib/native/founding-offer";

describe("web founding offer link-out", () => {
  it("allows the website", () => {
    expect(mayMentionWebFoundingOffer("web", null)).toBe(true);
  });

  it("allows only the US App Store storefront", () => {
    expect(appleStorefrontAllowsWebFoundingLink("USA")).toBe(true);
    expect(appleStorefrontAllowsWebFoundingLink("us")).toBe(true);
    expect(mayMentionWebFoundingOffer("ios", "USA")).toBe(true);
    expect(mayMentionWebFoundingOffer("ios", "GBR")).toBe(false);
    expect(mayMentionWebFoundingOffer("ios", null)).toBe(false);
  });

  it("never mentions the founding price on Android", () => {
    expect(mayMentionWebFoundingOffer("android", "US")).toBe(false);
  });
});
