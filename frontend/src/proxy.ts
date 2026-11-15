import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Define public routes that don't require authentication.
 * All other routes will require a signed-in user.
 */
export const publicRoutePatterns = [
  "/",                // landing
  "/pricing(.*)",
  "/privacy(.*)",
  "/terms(.*)",
  "/delete-account(.*)", // public account-deletion URL (Google Play)
  "/whats-new(.*)",   // public changelog (marketing footer)
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/sso-callback(.*)",
  "/sitemap.xml",     // .xml/.txt aren't excluded by the matcher below
  "/robots.txt",
];

const isPublicRoute = createRouteMatcher(publicRoutePatterns);

export default clerkMiddleware(async (auth, request) => {
  // Protect all routes except public ones
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals, the Sentry tunnel (next.config.ts), the ChatGPT
    // connector's endpoints proxied to the backend (MCP, OAuth, discovery:
    // they carry their own bearer tokens, which Clerk must not try to read),
    // and all static files, unless found in search params
    "/((?!_next|monitoring|api/mcp|api/oauth|\\.well-known|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // The app has no Next.js API routes of its own; /api/* paths are the
    // connector proxies above, so the old "always run for /api" entry is gone.
    "/trpc(.*)",
  ],
};
