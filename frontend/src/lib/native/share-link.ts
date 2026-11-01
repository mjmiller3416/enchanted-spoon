/** Pull the first http(s) URL out of share-sheet text (TikTok, Instagram, etc.). */
export function extractSharedRecipeUrl(text: string): string | null {
  const match = text.match(/https?:\/\/[^\s<>"']+/i);
  if (!match) return null;
  return match[0].replace(/[),.;]+$/g, "");
}

/**
 * `enchantedspoon://import?url=` from the share extension or an Android SEND intent.
 * Returns the recipe URL, or null when this deep link is something else.
 */
export function importUrlFromDeepLink(href: string): string | null {
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    return null;
  }
  if (url.protocol !== "enchantedspoon:") return null;
  const host = url.hostname || url.host;
  if (host !== "import") return null;
  const shared = url.searchParams.get("url");
  if (!shared) return null;
  return extractSharedRecipeUrl(shared);
}

export function isOAuthCallback(href: string): boolean {
  try {
    const url = new URL(href);
    return url.protocol === "enchantedspoon:" && (url.hostname || url.host) === "sso-callback";
  } catch {
    return false;
  }
}
