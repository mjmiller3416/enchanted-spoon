import type { MetadataRoute } from "next";

// Render at request time so BASE_URL comes from the runtime env. On Railway,
// NEXT_PUBLIC_APP_URL is absent during static generation, so a build-time read
// would bake in the localhost fallback.
export const dynamic = "force-dynamic";

export default function sitemap(): MetadataRoute.Sitemap {
  const BASE_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  return [
    {
      url: BASE_URL,
      changeFrequency: "monthly",
      priority: 1,
    },
    {
      url: `${BASE_URL}/pricing`,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${BASE_URL}/whats-new`,
      changeFrequency: "weekly",
      priority: 0.5,
    },
    {
      url: `${BASE_URL}/privacy`,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/terms`,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${BASE_URL}/sign-in`,
      changeFrequency: "yearly",
      priority: 0.4,
    },
    {
      url: `${BASE_URL}/sign-up`,
      changeFrequency: "yearly",
      priority: 0.4,
    },
  ];
}
