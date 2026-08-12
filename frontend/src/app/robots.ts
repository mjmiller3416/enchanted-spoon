import type { MetadataRoute } from "next";

// Render at request time so BASE_URL comes from the runtime env. On Railway,
// NEXT_PUBLIC_APP_URL is absent during static generation, so a build-time read
// would bake in the localhost fallback.
export const dynamic = "force-dynamic";

export default function robots(): MetadataRoute.Robots {
  const BASE_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // App routes are auth-gated anyway; keep crawlers out of them
        disallow: [
          "/dashboard",
          "/recipes",
          "/meal-planner",
          "/shopping-list",
          "/settings",
          "/admin",
          "/sso-callback",
          "/api/",
        ],
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
