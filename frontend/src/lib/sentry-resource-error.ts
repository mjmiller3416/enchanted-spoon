/**
 * Promise rejections whose reason is a resource `error` event
 * (`script.onerror = reject`) carry no stack. Describe the element so Sentry
 * can name the failed resource, and flag browser-extension URLs so they can
 * be dropped.
 *
 * Do not reference the DOM `Event` constructor. The same helper runs in the
 * Next.js server and edge runtimes via `sentry.ts`.
 */

const EXTENSION_PREFIXES = [
  "chrome-extension:",
  "moz-extension:",
  "safari-web-extension:",
  "safari-extension:",
] as const;

export type ResourceErrorExtras = {
  tagName: string | null;
  src: string | null;
  href: string | null;
};

export type ResourceErrorRejection =
  | { ignore: true }
  | { ignore: false; message: string; extras: ResourceErrorExtras };

const UNKNOWN_MESSAGE = "Failed to load resource (unknown)";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isErrorReason(reason: unknown): boolean {
  try {
    return reason instanceof Error;
  } catch {
    return false;
  }
}

function readString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function isExtensionUrl(url: string): boolean {
  const lower = url.toLowerCase();
  return EXTENSION_PREFIXES.some((prefix) => lower.startsWith(prefix));
}

function emptyExtras(): ResourceErrorExtras {
  return { tagName: null, src: null, href: null };
}

function readTarget(reason: Record<string, unknown>): ResourceErrorExtras {
  try {
    const target = reason.target;
    if (!isRecord(target)) return emptyExtras();
    return {
      tagName: readString(target.tagName),
      src: readString(target.src),
      href: readString(target.href),
    };
  } catch {
    return emptyExtras();
  }
}

function resourceMessage(extras: ResourceErrorExtras): string {
  const url = extras.src ?? extras.href;
  const tag = extras.tagName?.toLowerCase() ?? null;
  if (tag && url) return `Failed to load ${tag} ${url}`;
  if (url) return `Failed to load resource ${url}`;
  return UNKNOWN_MESSAGE;
}

/**
 * Returns null when `reason` is not an error event (including `Error` and
 * string rejections). Extension script/img/link URLs return `{ ignore: true }`.
 */
export function describeResourceErrorRejection(reason: unknown): ResourceErrorRejection | null {
  if (isErrorReason(reason) || !isRecord(reason) || reason.type !== "error") return null;

  const extras = readTarget(reason);
  if ((extras.src && isExtensionUrl(extras.src)) || (extras.href && isExtensionUrl(extras.href))) {
    return { ignore: true };
  }

  return { ignore: false, message: resourceMessage(extras), extras };
}
