import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { QueryProvider } from "@/lib/providers/QueryProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"),
  title: {
    default: "Whiskful — Recipes, meal planning, and smart shopping lists",
    template: "%s · Whiskful",
  },
  description:
    "Save recipes, plan your week, and get an auto-built shopping list. AI-powered recipe import and generation.",
  openGraph: {
    siteName: "Whiskful",
    type: "website",
    url: "/",
  },
  twitter: { card: "summary_large_image" },
};

// Runs synchronously before any content paints so a stored light preference
// never flashes the default dark theme. Reads the same key useSettings writes
// ("meal-genie-theme", JSON-encoded), falls back to the legacy "theme" key.
// An explicit "system" preference follows the OS; with no stored preference at
// all we default to dark. Keep in sync with hooks/ui/useTheme.ts.
const themeInitScript = `(function () {
  try {
    var pref = null;
    var raw = localStorage.getItem("meal-genie-theme");
    if (raw) {
      try { pref = JSON.parse(raw); } catch (e) { pref = raw; }
    }
    if (pref !== "light" && pref !== "dark" && pref !== "system") {
      pref = localStorage.getItem("theme");
    }
    var resolved;
    if (pref === "light" || pref === "dark") {
      resolved = pref;
    } else if (pref === "system") {
      resolved = window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark";
    } else {
      resolved = "dark";
    }
    document.documentElement.classList.toggle("light", resolved === "light");
  } catch (e) {}
})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
        suppressHydrationWarning
      >
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <ClerkProvider>
          <QueryProvider>
            {children}
            <Toaster />
          </QueryProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
