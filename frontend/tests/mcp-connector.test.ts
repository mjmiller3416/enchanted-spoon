import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouteMatcher } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";
import { config, publicRoutePatterns } from "@/proxy";
import { getPostAuthRedirect } from "@/lib/authRedirect";
import { oauthApi } from "@/lib/api";
import type { AuthorizeParams } from "@/types/oauth";

const isPublicRoute = createRouteMatcher(publicRoutePatterns);
const pageMatcher = new RegExp(`^${config.matcher[0]}$`);

const params: AuthorizeParams = {
  response_type: "code",
  client_id: "abc",
  redirect_uri: "https://chatgpt.com/connector_platform_oauth_redirect",
  code_challenge: "x".repeat(43),
  code_challenge_method: "S256",
  state: "s1",
  scope: "mcp",
  resource: null,
};

describe("ChatGPT connector routing", () => {
  it("keeps Clerk off the proxied MCP, OAuth and discovery paths", () => {
    for (const path of [
      "/api/mcp",
      "/api/oauth/token",
      "/api/oauth/register",
      "/.well-known/oauth-authorization-server",
      "/.well-known/oauth-protected-resource/api/mcp",
    ]) {
      expect(pageMatcher.test(path), path).toBe(false);
    }
  });

  it("puts the consent page behind sign-in", () => {
    expect(pageMatcher.test("/oauth/authorize")).toBe(true);
    const request = new NextRequest(new URL("/oauth/authorize?client_id=abc", "http://localhost:3000"));
    expect(isPublicRoute(request)).toBe(false);
  });

  it("returns to the consent page with its whole query after sign-in", () => {
    const consent = "/oauth/authorize?response_type=code&client_id=abc&state=s1&code_challenge_method=S256";
    window.history.replaceState(null, "", `/sign-in?redirect_url=${encodeURIComponent(consent)}`);
    expect(getPostAuthRedirect()).toBe(consent);
    window.history.replaceState(null, "", "/");
  });
});

describe("oauthApi", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("checks a request with its query and decides with the Clerk token", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ redirect_to: "https://chatgpt.com/cb?code=1" })));
    vi.stubGlobal("fetch", fetchMock);

    await oauthApi.check(params);
    const checkUrl = String((fetchMock.mock.calls[0] as unknown[])[0]);
    expect(checkUrl).toContain("/api/oauth/authorize/check?");
    expect(checkUrl).toContain("client_id=abc");
    expect(checkUrl).not.toContain("resource=");

    const result = await oauthApi.decide(params, "allow", "clerk-token");
    expect(result.redirect_to).toBe("https://chatgpt.com/cb?code=1");
    const [url, init] = fetchMock.mock.calls[1] as unknown as [string, RequestInit];
    expect(url).toContain("/api/oauth/authorize");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer clerk-token");
    expect(JSON.parse(String(init.body))).toMatchObject({ client_id: "abc", decision: "allow" });
  });
});
