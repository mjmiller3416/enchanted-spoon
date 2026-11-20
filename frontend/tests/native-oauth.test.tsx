import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NativeRuntime } from "@/components/native/NativeRuntime";
import { clerkFrontendHost } from "@/lib/native/clerk-publishable-key";
import { API_BASE } from "@/lib/api/base";
import {
  NATIVE_AUTH_EVENT,
  NATIVE_OAUTH_REDIRECT,
  nativeOAuthFailureMessage,
  resetNativeOAuthState,
  setNativeOAuthLocationAssignForTests,
  startNativeOAuth,
  type NativeAuthDetail,
} from "@/lib/native/native-oauth";

const HOST = "clerk.example.test";
const PUBLISHABLE_KEY = `pk_test_${btoa(`${HOST}$`)}`;
const GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth?client_id=test";
const SESSION_JWT = "header.payload.signature";
const TICKET = "ticket_one";

const capacitor = vi.hoisted(() => {
  const appListeners = new Map<string, (event: { url: string }) => void>();
  const browserListeners = new Map<string, () => void>();
  return {
    appListeners,
    browserListeners,
    open: vi.fn(async () => undefined),
    close: vi.fn(async () => undefined),
    httpRequest: vi.fn(),
  };
});

vi.mock("@capacitor/core", () => ({
  CapacitorHttp: { request: capacitor.httpRequest },
}));

vi.mock("@capacitor/app", () => ({
  App: {
    addListener: vi.fn(async (name: string, callback: (event: { url: string }) => void) => {
      capacitor.appListeners.set(name, callback);
      return { remove: vi.fn() };
    }),
  },
}));

vi.mock("@capacitor/browser", () => ({
  Browser: {
    open: capacitor.open,
    close: capacitor.close,
    addListener: vi.fn(async (name: string, callback: () => void) => {
      capacitor.browserListeners.set(name, callback);
      return { remove: vi.fn() };
    }),
  },
}));

vi.mock("@capacitor/splash-screen", () => ({
  SplashScreen: { hide: vi.fn(async () => undefined) },
}));

const captureException = vi.hoisted(() => vi.fn());

vi.mock("@sentry/nextjs", () => ({
  captureException,
}));

const toastError = vi.hoisted(() => vi.fn());

vi.mock("sonner", () => ({
  toast: { error: toastError },
}));

const signInCreate = vi.fn(async () => ({ status: "complete", createdSessionId: "sess_browser" }));
const setActive = vi.fn(async () => undefined);
const assign = vi.fn();

function jsonResponse(body: unknown, authorization?: string, status = 200): Response {
  const headers = new Headers();
  if (authorization) headers.set("authorization", authorization);
  return new Response(JSON.stringify(body), { status, headers });
}

function installClerk(): void {
  (window as unknown as { Clerk: unknown }).Clerk = {
    publishableKey: PUBLISHABLE_KEY,
    client: { signIn: { create: signInCreate } },
    setActive,
  };
}

function installCapacitor(): void {
  window.Capacitor = {
    isNativePlatform: () => true,
    getPlatform: () => "android",
  };
}

describe("clerk publishable key", () => {
  it("reads the Frontend API host embedded in the key", () => {
    expect(clerkFrontendHost(PUBLISHABLE_KEY)).toBe(HOST);
    expect(clerkFrontendHost("pk_live_" + btoa("clerk.enchantedspoon.app$"))).toBe(
      "clerk.enchantedspoon.app",
    );
    expect(clerkFrontendHost("not-a-key")).toBeNull();
    expect(clerkFrontendHost("pk_test_@@@")).toBeNull();
  });
});

describe("native OAuth", () => {
  const calls: Array<{ url: string; init: RequestInit; via: "fetch" | "native" }> = [];
  let mode: "existing" | "transfer" | "rejected" = "existing";

  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    resetNativeOAuthState();
    sessionStorage.clear();
    calls.length = 0;
    mode = "existing";
    capacitor.open.mockClear();
    capacitor.close.mockClear();
    capacitor.appListeners.clear();
    capacitor.browserListeners.clear();
    signInCreate.mockClear();
    setActive.mockClear();
    assign.mockReset();
    toastError.mockReset();
    installClerk();
    installCapacitor();
    setNativeOAuthLocationAssignForTests(assign);

    captureException.mockReset();
    capacitor.httpRequest.mockReset();

    // The WebView's fetch always sends `Origin`, and Clerk's Frontend API
    // answers Origin plus Authorization with a 400. The native HTTP client
    // sends no Origin. This stub reproduces that rule.
    capacitor.httpRequest.mockImplementation(
      async (options: {
        url: string;
        method: string;
        headers?: Record<string, string>;
        data?: Record<string, string>;
      }) => {
        const init: RequestInit = {
          method: options.method,
          headers: options.headers,
          body: options.data ? new URLSearchParams(options.data).toString() : undefined,
        };
        calls.push({ url: options.url, init, via: "native" });
        const response = await respond(options.url);
        const headers: Record<string, string> = {};
        response.headers.forEach((value, key) => {
          headers[key] = value;
        });
        return { status: response.status, headers, data: await response.text(), url: options.url };
      },
    );

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const request = init ?? {};
        calls.push({ url, init: request, via: "fetch" });
        if (url.startsWith(`https://${HOST}/`) && new Headers(request.headers).has("authorization")) {
          return jsonResponse(
            {
              errors: [
                { message: "Origin and Authorization", code: "origin_authorization_headers_conflict" },
              ],
            },
            undefined,
            400,
          );
        }
        return respond(url);
      }),
    );

    async function respond(url: string): Promise<Response> {
      {
        if (url.includes("/api/auth/native-ticket")) {
          return jsonResponse({ ticket: TICKET });
        }
        if (url.includes("/client/sign_ups")) {
          return jsonResponse(
            {
              response: {
                id: "sua_1",
                status: "complete",
                created_session_id: "sess_new",
              },
            },
            "native-client-after-transfer",
          );
        }
        if (url.includes("/tokens")) {
          return jsonResponse({ response: { object: "token", jwt: SESSION_JWT } });
        }
        if (url.includes("/client/sign_ins/sia_1")) {
          if (mode === "rejected") {
            return jsonResponse(
              { errors: [{ message: "Unauthorized request", code: "authorization_invalid" }] },
              undefined,
              401,
            );
          }
          if (mode === "transfer") {
            return jsonResponse(
              {
                response: {
                  id: "sia_1",
                  status: "needs_first_factor",
                  created_session_id: null,
                  first_factor_verification: { status: "transferable", strategy: "oauth_google" },
                },
              },
              "native-client-token-2",
            );
          }
          return jsonResponse(
            {
              response: {
                id: "sia_1",
                status: "complete",
                created_session_id: "sess_existing",
                first_factor_verification: { status: "verified", strategy: "oauth_google" },
              },
            },
            "native-client-token-2",
          );
        }
        if (url.includes("/client/sign_ins")) {
          return jsonResponse(
            {
              response: {
                id: "sia_1",
                status: "needs_first_factor",
                first_factor_verification: {
                  status: "unverified",
                  strategy: "oauth_google",
                  external_verification_redirect_url: GOOGLE_URL,
                },
              },
            },
            "native-client-token",
          );
        }
        return jsonResponse({ errors: [{ message: "unexpected", code: "unexpected" }] }, undefined, 404);
      }
    }
  });

  async function openCallbackListener(): Promise<(event: { url: string }) => void> {
    render(<NativeRuntime />);
    await waitFor(() => {
      expect(capacitor.appListeners.has("appUrlOpen")).toBe(true);
      expect(capacitor.appListeners.has("backButton")).toBe(true);
    });
    const listener = capacitor.appListeners.get("appUrlOpen");
    if (!listener) throw new Error("appUrlOpen listener was not registered");
    return listener;
  }

  function clerkCalls(): Array<{ url: string; init: RequestInit; via: "fetch" | "native" }> {
    return calls.filter((call) => call.url.startsWith(`https://${HOST}/`));
  }

  it("starts a native sign-in and opens the provider in the system browser", async () => {
    await startNativeOAuth("oauth_google");

    expect(clerkCalls()).toHaveLength(1);
    const [created] = clerkCalls();
    expect(created.url).toContain("/v1/client/sign_ins?");
    expect(created.url).toContain("_is_native=1");
    expect(created.init.method).toBe("POST");
    expect(created.via).toBe("native");
    expect(created.init.body).toBe(
      `strategy=oauth_google&redirect_url=${encodeURIComponent(NATIVE_OAUTH_REDIRECT)}`,
    );
    expect(String(created.init.body)).not.toContain("redirect_url_complete");
    expect(new Headers(created.init.headers).has("authorization")).toBe(false);
    expect(capacitor.open).toHaveBeenCalledWith({ url: GOOGLE_URL });
  });

  it("starts Apple the same way", async () => {
    await startNativeOAuth("oauth_apple");
    const body = String(clerkCalls()[0]?.init.body);
    expect(body).toContain("strategy=oauth_apple");
    expect(body).toContain(`redirect_url=${encodeURIComponent(NATIVE_OAUTH_REDIRECT)}`);
    expect(capacitor.open).toHaveBeenCalledWith({ url: GOOGLE_URL });
  });

  it("refuses a provider URL that is not https", async () => {
    capacitor.httpRequest.mockImplementation(async () => ({
      status: 200,
      headers: { authorization: "native-client-token" },
      data: JSON.stringify({
        response: {
          id: "sia_1",
          first_factor_verification: {
            external_verification_redirect_url: "javascript:alert(1)",
          },
        },
      }),
    }));

    await expect(startNativeOAuth("oauth_google")).rejects.toThrow(nativeOAuthFailureMessage("oauth_google"));
    expect(capacitor.open).not.toHaveBeenCalled();
  });

  it("completes an existing user from appUrlOpen with a ticket sign-in", async () => {
    const onOpen = await openCallbackListener();
    await startNativeOAuth("oauth_google");

    onOpen({ url: "enchantedspoon://sso-callback?rotating_token_nonce=nonce_value_12345" });

    await waitFor(() => {
      expect(setActive).toHaveBeenCalledWith({ session: "sess_browser" });
    });

    const reload = clerkCalls().find((call) => call.url.includes("/client/sign_ins/sia_1"));
    expect(reload?.init.method).toBe("GET");
    expect(reload?.via).toBe("native");
    expect(reload?.url).toContain("_is_native=1");
    expect(reload?.url).toContain("rotating_token_nonce=nonce_value_12345");
    expect(new Headers(reload?.init.headers).get("authorization")).toBe("native-client-token");

    const minted = clerkCalls().find((call) => call.url.includes("/sessions/sess_existing/tokens"));
    expect(minted?.init.method).toBe("POST");
    expect(minted?.via).toBe("native");
    expect(new Headers(minted?.init.headers).get("authorization")).toBe("native-client-token-2");

    const ticket = calls.find((call) => call.url === `${API_BASE}/api/auth/native-ticket`);
    expect(ticket?.init.method).toBe("POST");
    expect(new Headers(ticket?.init.headers).get("authorization")).toBe(`Bearer ${SESSION_JWT}`);
    expect(signInCreate).toHaveBeenCalledWith({ strategy: "ticket", ticket: TICKET });
    expect(assign).toHaveBeenCalledWith("/dashboard");
    expect(capacitor.close).toHaveBeenCalled();
    expect(clerkCalls().some((call) => call.url.includes("/client/sign_ups"))).toBe(false);
    expect(captureException).not.toHaveBeenCalled();
  });

  it("never sends a Clerk Frontend API call through the WebView's fetch", async () => {
    // Clerk answers Origin plus Authorization with 400, and a WebView always
    // adds Origin. Only Capacitor's native HTTP client may talk to Clerk.
    const onOpen = await openCallbackListener();
    await startNativeOAuth("oauth_google");
    onOpen({ url: "enchantedspoon://sso-callback?rotating_token_nonce=nonce_value_12345" });
    await waitFor(() => expect(setActive).toHaveBeenCalled());

    expect(clerkCalls().length).toBeGreaterThanOrEqual(3);
    expect(clerkCalls().every((call) => call.via === "native")).toBe(true);
    expect(clerkCalls().every((call) => !("credentials" in call.init))).toBe(true);
    expect(toastError).not.toHaveBeenCalled();
  });

  async function failCallback(): Promise<void> {
    const seen: NativeAuthDetail[] = [];
    const onResult = (event: Event) => {
      event.preventDefault();
      seen.push((event as CustomEvent<NativeAuthDetail>).detail);
    };
    window.addEventListener(NATIVE_AUTH_EVENT, onResult);
    const onOpen = await openCallbackListener();
    await startNativeOAuth("oauth_google");
    onOpen({ url: "enchantedspoon://sso-callback?rotating_token_nonce=nonce_value_12345" });
    await waitFor(() => expect(seen.some((detail) => detail.status === "error")).toBe(true));
    window.removeEventListener(NATIVE_AUTH_EVENT, onResult);
  }

  function reported(): { message: string; tags: Record<string, string> } {
    expect(captureException).toHaveBeenCalledTimes(1);
    const [error, hint] = captureException.mock.calls[0] as [
      Error,
      { tags: Record<string, string> },
    ];
    return { message: error.message, tags: hint.tags };
  }

  it("reports the failing step, HTTP status and Clerk code to Sentry", async () => {
    mode = "rejected";
    await failCallback();

    const { message, tags } = reported();
    expect(message).toBe("Native sign-in failed at reload_sign_in - HTTP 401 - authorization_invalid");
    expect(tags).toEqual({
      native_oauth_step: "reload_sign_in",
      native_oauth_strategy: "oauth_google",
      native_oauth_status: "401",
      native_oauth_clerk_code: "authorization_invalid",
    });
    expect(JSON.stringify(captureException.mock.calls)).not.toContain("native-client-token");
  });

  it("reports a Clerk Frontend API call that never got an answer", async () => {
    const original = capacitor.httpRequest.getMockImplementation();
    let attempts = 0;
    capacitor.httpRequest.mockImplementation(async (options: unknown) => {
      attempts += 1;
      if (attempts > 1) throw new Error("offline");
      return original?.(options);
    });
    await failCallback();

    const { tags } = reported();
    expect(tags.native_oauth_step).toBe("reload_sign_in");
    expect(tags.native_oauth_status).toBe("0");
    expect(tags.native_oauth_clerk_code).toBe("network_error");
  });

  it("reports a failed ticket exchange with the backend status", async () => {
    const original = vi.mocked(fetch).getMockImplementation();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        if (String(input).includes("/api/auth/native-ticket")) {
          return jsonResponse({ detail: "Sign-in could not be completed." }, undefined, 502);
        }
        return original?.(input, init);
      }),
    );
    await failCallback();

    const { message, tags } = reported();
    expect(message).toBe("Native sign-in failed at ticket_exchange - HTTP 502");
    expect(tags.native_oauth_step).toBe("ticket_exchange");
    expect(tags.native_oauth_status).toBe("502");
    expect(tags.native_oauth_clerk_code).toBeUndefined();
    expect(signInCreate).not.toHaveBeenCalled();
  });

  it("reports a ticket Clerk refuses with Clerk's code", async () => {
    signInCreate.mockRejectedValueOnce({ errors: [{ code: "ticket_invalid" }] });
    await failCallback();

    const { tags } = reported();
    expect(tags.native_oauth_step).toBe("ticket_activate");
    expect(tags.native_oauth_clerk_code).toBe("ticket_invalid");
    expect(setActive).not.toHaveBeenCalled();
  });

  it("reports a callback that arrives with no sign-in in progress", async () => {
    const onOpen = await openCallbackListener();
    const seen: NativeAuthDetail[] = [];
    const onResult = (event: Event) => {
      event.preventDefault();
      seen.push((event as CustomEvent<NativeAuthDetail>).detail);
    };
    window.addEventListener(NATIVE_AUTH_EVENT, onResult);
    onOpen({ url: "enchantedspoon://sso-callback?rotating_token_nonce=nonce_value_12345" });
    await waitFor(() => expect(seen).toHaveLength(1));
    window.removeEventListener(NATIVE_AUTH_EVENT, onResult);

    expect(reported().tags.native_oauth_step).toBe("no_pending_sign_in");
    expect(capacitor.httpRequest).not.toHaveBeenCalled();
  });

  it("reports a sign-in that Clerk will not start", async () => {
    capacitor.httpRequest.mockImplementation(async () => ({
      status: 403,
      headers: {},
      data: JSON.stringify({ errors: [{ code: "native_api_disabled" }] }),
    }));

    await expect(startNativeOAuth("oauth_google")).rejects.toThrow(
      nativeOAuthFailureMessage("oauth_google"),
    );
    const { tags } = reported();
    expect(tags.native_oauth_step).toBe("start");
    expect(tags.native_oauth_status).toBe("403");
    expect(tags.native_oauth_clerk_code).toBe("native_api_disabled");
  });

  it("transfers a new Google user to sign-up before the ticket", async () => {
    mode = "transfer";
    const onOpen = await openCallbackListener();
    await startNativeOAuth("oauth_google");
    onOpen({ url: "enchantedspoon://sso-callback?rotating_token_nonce=nonce_value_12345" });

    await waitFor(() => {
      expect(signInCreate).toHaveBeenCalledWith({ strategy: "ticket", ticket: TICKET });
    });

    const transfer = clerkCalls().find((call) => call.url.includes("/client/sign_ups"));
    expect(transfer?.init.method).toBe("POST");
    expect(transfer?.via).toBe("native");
    expect(transfer?.url).toContain("_is_native=1");
    expect(transfer?.init.body).toBe("transfer=true");
    expect(new Headers(transfer?.init.headers).get("authorization")).toBe("native-client-token-2");

    const minted = clerkCalls().find((call) => call.url.includes("/sessions/sess_new/tokens"));
    expect(new Headers(minted?.init.headers).get("authorization")).toBe("native-client-after-transfer");
    expect(setActive).toHaveBeenCalledWith({ session: "sess_browser" });
  });

  it("shows a friendly error instead of Clerk's JSON", async () => {
    mode = "rejected";
    const seen: NativeAuthDetail[] = [];
    const onResult = (event: Event) => {
      event.preventDefault();
      seen.push((event as CustomEvent<NativeAuthDetail>).detail);
    };
    window.addEventListener(NATIVE_AUTH_EVENT, onResult);

    const onOpen = await openCallbackListener();
    await startNativeOAuth("oauth_google");
    onOpen({ url: "enchantedspoon://sso-callback?rotating_token_nonce=nonce_value_12345" });

    await waitFor(() => {
      expect(seen.some((detail) => detail.status === "error")).toBe(true);
    });

    const error = seen.find((detail) => detail.status === "error");
    expect(error).toEqual({ status: "error", message: nativeOAuthFailureMessage("oauth_google") });
    if (error?.status === "error") {
      expect(error.message).not.toMatch(/AI|authorization_invalid|Unauthorized|\{/);
      expect(error.message).toContain("Google sign-in didn't finish");
    }
    expect(signInCreate).not.toHaveBeenCalled();
    expect(toastError).not.toHaveBeenCalled();

    window.removeEventListener(NATIVE_AUTH_EVENT, onResult);
  });
});
