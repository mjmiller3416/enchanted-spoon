/**
 * Google and Apple sign-in inside the Capacitor shell.
 *
 * The WebView and the system browser (Custom Tab / SFSafariViewController)
 * do not share cookies. clerk-js 5.121.1's Frontend API client always sends
 * `credentials: "include"` and never sets `_is_native`, so a sign-in created
 * by the page's Clerk instance dies on `https://<frontend-api>/v1/oauth_callback`
 * with `authorization_invalid`: Clerk looks up the `__client` cookie and the
 * Custom Tab does not have it.
 *
 * clerk-expo does not switch the whole app out of standard-browser mode. It
 * keeps a native client: every Frontend API call uses `?_is_native=1`, omits
 * cookies, and replays the `Authorization` header Clerk returns. The provider
 * then redirects to the app scheme with `rotating_token_nonce`, and
 * `signIn.reload({ rotatingTokenNonce })` finishes on that same client.
 * A second `Clerk()` instance cannot do this here: constructing one replaces
 * `BaseResource.clerk` for the Next.js provider and would drop the cookie
 * session the middleware and SSR depend on. `standardBrowser: false` in
 * 5.121.1 still uses cookies on the Frontend API.
 *
 * This module is that native client, and only for the OAuth attempt. When
 * the native client has a session JWT, the backend trades it for a one-minute
 * sign-in token. The WebView's real Clerk accepts the token with
 * `signIn.create({ strategy: "ticket" })`, which sets the normal cookie session.
 * The browser `authenticateWithRedirect` path is not used here.
 */

import * as Sentry from "@sentry/nextjs";
import { toast } from "sonner";

import { API_BASE } from "@/lib/api/base";
import { getPostAuthRedirect } from "@/lib/authRedirect";
import { appConfig } from "@/lib/config";
import { clerkFrontendHost } from "@/lib/native/clerk-publishable-key";
import { nativeClientHeaders } from "@/lib/native/platform";
import type { HostedOAuthStrategy } from "@/lib/native/social-sign-in";

export const NATIVE_OAUTH_REDIRECT = "enchantedspoon://sso-callback";
export const NATIVE_AUTH_EVENT = "enchantedspoon:native-auth";

/** clerk-js 5.121.1 sends these on every Frontend API request. */
const CLERK_API_VERSION = "2025-11-10";
const CLERK_JS_VERSION = "5.121.1";
const PENDING_KEY = "enchantedspoon.native-oauth";
const BROWSER_CLOSE_GRACE_MS = 700;

export class NativeOAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NativeOAuthError";
  }
}

export type NativeAuthDetail =
  | { status: "error"; message: string }
  | { status: "cancelled" }
  | { status: "success" };

interface PendingNativeAuth {
  authorization: string;
  signInId: string;
  strategy: HostedOAuthStrategy;
}

interface TicketSignIn {
  create: (params: { strategy: "ticket"; ticket: string }) => Promise<{
    status?: string | null;
    createdSessionId?: string | null;
  }>;
}

interface BrowserClerk {
  publishableKey?: string;
  client?: { signIn?: TicketSignIn } | null;
  setActive?: (params: { session: string }) => Promise<unknown>;
}

type Phase = "idle" | "pending" | "completing";

let phase: Phase = "idle";
let busy = false;
let memoryPending: PendingNativeAuth | null = null;
let closeTimer: ReturnType<typeof setTimeout> | null = null;

function defaultAssign(path: string): void {
  window.location.assign(path);
}

let assignLocation = defaultAssign;

/** Tests replace navigation because jsdom will not let us spy on location.assign. */
export function setNativeOAuthLocationAssignForTests(assign: (path: string) => void): void {
  assignLocation = assign;
}

function providerName(strategy: HostedOAuthStrategy | null): string {
  if (strategy === "oauth_apple") return "Apple";
  if (strategy === "oauth_google") return "Google";
  return "Sign-in";
}

export function nativeOAuthFailureMessage(strategy: HostedOAuthStrategy | null): string {
  const provider = providerName(strategy);
  const what = strategy ? `${provider} sign-in` : "Sign-in";
  return `${what} didn't finish. Please try again, or email ${appConfig.supportEmail}.`;
}

function browserClerk(): BrowserClerk | null {
  if (typeof window === "undefined") return null;
  const clerk = (window as { Clerk?: BrowserClerk }).Clerk;
  return clerk ?? null;
}

function publishableKey(): string | null {
  const fromClerk = browserClerk()?.publishableKey;
  if (typeof fromClerk === "string" && fromClerk.trim()) return fromClerk.trim();
  const fromEnv = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  return typeof fromEnv === "string" && fromEnv.trim() ? fromEnv.trim() : null;
}

function isStrategy(value: unknown): value is HostedOAuthStrategy {
  return value === "oauth_google" || value === "oauth_apple";
}

function safeHeader(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 4096 && !/[\r\n]/.test(value);
}

function safeResourceId(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9_]{1,128}$/.test(value);
}

function safeNonce(value: string): boolean {
  return /^[A-Za-z0-9._~+/=-]{8,512}$/.test(value);
}

function httpsUrl(value: unknown): string | null {
  if (typeof value !== "string" || value.length > 4096) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:") return null;
    return url.toString();
  } catch {
    return null;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object") return null;
  return value as Record<string, unknown>;
}

function resourceOf(payload: unknown): Record<string, unknown> | null {
  const root = asRecord(payload);
  if (!root) return null;
  return asRecord(root.response) ?? root;
}

function errorCode(payload: unknown): string | null {
  const errors = asRecord(payload)?.errors;
  if (!Array.isArray(errors)) return null;
  const code = asRecord(errors[0])?.code;
  return typeof code === "string" ? code : null;
}

function verificationStatus(resource: Record<string, unknown> | null): string | null {
  const status = asRecord(resource?.first_factor_verification)?.status;
  return typeof status === "string" ? status : null;
}

function isTransferable(resource: Record<string, unknown> | null): boolean {
  if (!resource) return false;
  if (resource.status === "transferable") return true;
  return verificationStatus(resource) === "transferable";
}

function sessionIdOf(resource: Record<string, unknown> | null): string | null {
  const id = resource?.created_session_id;
  return safeResourceId(id) && id.startsWith("sess_") ? id : null;
}

function readSessionJwt(payload: unknown): string | null {
  const resource = resourceOf(payload);
  const jwt = resource?.jwt;
  if (typeof jwt !== "string") return null;
  const parts = jwt.split(".");
  if (parts.length !== 3 || parts.some((part) => part.length === 0)) return null;
  if (jwt.length > 8192) return null;
  return jwt;
}

function externalVerificationUrl(resource: Record<string, unknown> | null): string | null {
  const verification = asRecord(resource?.first_factor_verification);
  return httpsUrl(verification?.external_verification_redirect_url);
}

function savePending(pending: PendingNativeAuth): void {
  memoryPending = pending;
  try {
    sessionStorage.setItem(PENDING_KEY, JSON.stringify(pending));
  } catch {
    // The in-memory copy is enough while this document stays alive.
  }
}

function loadPending(): PendingNativeAuth | null {
  if (memoryPending && isStrategy(memoryPending.strategy) && safeHeader(memoryPending.authorization)) {
    return memoryPending;
  }
  try {
    const raw = sessionStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const parsed = asRecord(JSON.parse(raw));
    if (!parsed || !isStrategy(parsed.strategy) || !safeHeader(parsed.authorization)) return null;
    if (!safeResourceId(parsed.signInId)) return null;
    const pending: PendingNativeAuth = {
      authorization: parsed.authorization,
      signInId: parsed.signInId,
      strategy: parsed.strategy,
    };
    memoryPending = pending;
    return pending;
  } catch {
    return null;
  }
}

function clearPending(): void {
  memoryPending = null;
  try {
    sessionStorage.removeItem(PENDING_KEY);
  } catch {
    // Already gone.
  }
}

function publish(detail: NativeAuthDetail): void {
  if (typeof window === "undefined") return;
  const event = new CustomEvent<NativeAuthDetail>(NATIVE_AUTH_EVENT, {
    cancelable: true,
    detail,
  });
  window.dispatchEvent(event);
  if (detail.status === "error" && !event.defaultPrevented) {
    toast.error(detail.message);
  }
}

function reportFailure(): void {
  Sentry.captureException(new Error("Native sign-in could not be completed"));
}

export function resetNativeOAuthState(): void {
  phase = "idle";
  busy = false;
  memoryPending = null;
  assignLocation = defaultAssign;
  if (closeTimer) {
    clearTimeout(closeTimer);
    closeTimer = null;
  }
  clearPending();
}

/**
 * The Custom Tab closing is also how a finished sign-in returns to the app.
 * Wait briefly so a deep link that arrives in the same moment is not treated
 * as a cancellation.
 */
export function noteNativeBrowserClosed(): void {
  if (phase !== "pending") return;
  if (closeTimer) clearTimeout(closeTimer);
  closeTimer = setTimeout(() => {
    closeTimer = null;
    if (phase !== "pending") return;
    phase = "idle";
    publish({ status: "cancelled" });
  }, BROWSER_CLOSE_GRACE_MS);
}

function fapiUrl(host: string, path: string, search?: Record<string, string>): string {
  const url = new URL(`https://${host}/v1${path}`);
  url.searchParams.set("__clerk_api_version", CLERK_API_VERSION);
  url.searchParams.set("_clerk_js_version", CLERK_JS_VERSION);
  url.searchParams.set("_is_native", "1");
  if (search) {
    for (const [key, value] of Object.entries(search)) {
      url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

interface FapiResult {
  ok: boolean;
  payload: unknown;
  authorization: string | null;
  errorCode: string | null;
}

async function fapi(
  host: string,
  path: string,
  options: {
    method: "GET" | "POST";
    authorization: string | null;
    body?: Record<string, string>;
    search?: Record<string, string>;
  },
): Promise<FapiResult> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.authorization) headers.Authorization = options.authorization;
  let body: string | undefined;
  if (options.method === "POST") {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(options.body ?? {}).toString();
  }

  const response = await fetch(fapiUrl(host, path, options.search), {
    method: options.method,
    headers,
    body,
    credentials: "omit",
    cache: "no-store",
    redirect: "manual",
    referrerPolicy: "no-referrer",
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  const authorization = response.headers.get("authorization");
  return {
    ok: response.ok,
    payload,
    authorization: safeHeader(authorization) ? authorization : null,
    errorCode: errorCode(payload),
  };
}

async function closeSystemBrowser(): Promise<void> {
  try {
    const { Browser } = await import("@capacitor/browser");
    await Browser.close();
  } catch {
    // The tab may already be gone.
  }
}

export async function startNativeOAuth(strategy: HostedOAuthStrategy): Promise<void> {
  const host = clerkFrontendHost(publishableKey());
  if (!host) {
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }

  let created: FapiResult;
  try {
    created = await fapi(host, "/client/sign_ins", {
      method: "POST",
      authorization: null,
      body: { strategy, redirect_url: NATIVE_OAUTH_REDIRECT },
    });
  } catch {
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }

  const resource = resourceOf(created.payload);
  const signInId = resource?.id;
  const url = externalVerificationUrl(resource);
  if (!created.ok || !created.authorization || !safeResourceId(signInId) || !url) {
    clearPending();
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }

  savePending({ authorization: created.authorization, signInId, strategy });

  try {
    const { Browser } = await import("@capacitor/browser");
    await Browser.open({ url });
  } catch {
    clearPending();
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }
  phase = "pending";
}

async function exchangeSessionForTicket(
  sessionJwt: string,
  strategy: HostedOAuthStrategy,
): Promise<string> {
  const response = await fetch(`${API_BASE}/api/auth/native-ticket`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${sessionJwt}`,
      ...nativeClientHeaders(),
    },
    cache: "no-store",
    referrerPolicy: "no-referrer",
  });
  if (!response.ok) {
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }
  const ticket = asRecord(payload)?.ticket;
  if (typeof ticket !== "string" || ticket.length === 0 || ticket.length > 4000) {
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }
  return ticket;
}

async function activateBrowserSession(ticket: string, strategy: HostedOAuthStrategy): Promise<void> {
  const clerk = browserClerk();
  const signIn = clerk?.client?.signIn;
  if (!signIn || !clerk?.setActive) {
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }
  const result = await signIn.create({ strategy: "ticket", ticket });
  const sessionId = result?.createdSessionId;
  if (!sessionId || result.status !== "complete") {
    throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
  }
  await clerk.setActive({ session: sessionId });
}

/**
 * Finish `enchantedspoon://sso-callback?rotating_token_nonce=...` on the
 * native client that started the attempt, then hand the session to the
 * WebView's Clerk.
 */
export async function completeNativeOAuth(href: string): Promise<void> {
  if (busy) return;
  busy = true;
  phase = "completing";
  if (closeTimer) {
    clearTimeout(closeTimer);
    closeTimer = null;
  }
  void closeSystemBrowser();

  const pending = loadPending();
  clearPending();
  const strategy = pending?.strategy ?? null;

  try {
    if (!pending) throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));

    let callback: URL;
    try {
      callback = new URL(href);
    } catch {
      throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
    }
    const nonce = callback.searchParams.get("rotating_token_nonce") ?? "";
    if (!safeNonce(nonce)) throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));

    const host = clerkFrontendHost(publishableKey());
    if (!host) throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));

    let authorization = pending.authorization;
    const reloaded = await fapi(host, `/client/sign_ins/${pending.signInId}`, {
      method: "GET",
      authorization,
      search: { rotating_token_nonce: nonce },
    });
    if (reloaded.authorization) authorization = reloaded.authorization;
    if (!reloaded.ok) throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));

    let resource = resourceOf(reloaded.payload);
    let sessionId = sessionIdOf(resource);

    if (resource?.status !== "complete" && isTransferable(resource)) {
      const transferred = await fapi(host, "/client/sign_ups", {
        method: "POST",
        authorization,
        body: { transfer: "true" },
      });
      if (transferred.authorization) authorization = transferred.authorization;
      if (!transferred.ok) throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));
      resource = resourceOf(transferred.payload);
      sessionId = sessionIdOf(resource);
    }

    if (!sessionId) throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));

    const minted = await fapi(host, `/client/sessions/${sessionId}/tokens`, {
      method: "POST",
      authorization,
    });
    if (minted.authorization) authorization = minted.authorization;
    const sessionJwt = readSessionJwt(minted.payload);
    if (!minted.ok || !sessionJwt) throw new NativeOAuthError(nativeOAuthFailureMessage(strategy));

    const ticket = await exchangeSessionForTicket(sessionJwt, pending.strategy);
    await activateBrowserSession(ticket, pending.strategy);
    publish({ status: "success" });
    assignLocation(getPostAuthRedirect());
  } catch (err) {
    const message = err instanceof NativeOAuthError ? err.message : nativeOAuthFailureMessage(strategy);
    publish({ status: "error", message });
    reportFailure();
  } finally {
    busy = false;
    phase = "idle";
  }
}
