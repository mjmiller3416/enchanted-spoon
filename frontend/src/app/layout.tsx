import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";
import { NativeRuntime } from "@/components/native/NativeRuntime";
import { Toaster } from "@/components/ui/sonner";
import { QueryProvider } from "@/lib/providers/QueryProvider";
import { appConfig } from "@/lib/config";
import { themeInitScript } from "@/lib/theme-preference";

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
    default: `${appConfig.appName} — Recipes, meal planning, and shopping lists`,
    template: `%s · ${appConfig.appName}`,
  },
  description:
    "Save the recipes you cook, plan the week, and shop from one list.",
  openGraph: {
    siteName: appConfig.appName,
    type: "website",
    url: "/",
  },
  twitter: { card: "summary_large_image" },
  // Home-screen launches on older iOS read these instead of the manifest
  appleWebApp: { capable: true, title: appConfig.appName },
};

// Chromium fires `beforeinstallprompt` once per page load, often before React
// hydrates, so it's stashed on window here for PwaInstallProvider to pick up.
// preventDefault suppresses Chrome's own mini-infobar in favor of our prompt.
// Keep the global/event names in sync with lib/pwa.ts.
// Marks the document before paint when the Capacitor shell injected its bridge,
// so native-only CSS (hiding the web founding offer) applies without a flash.
const nativeClientScript = `(function () {
  try {
    var cap = window.Capacitor;
    if (cap && typeof cap.isNativePlatform === "function" && cap.isNativePlatform()) {
      var root = document.documentElement;
      root.classList.add("native-app");
      var platform = typeof cap.getPlatform === "function" ? cap.getPlatform() : "unknown";
      root.classList.add("native-" + platform);
    }
  } catch (e) {}
})();`;

const installPromptCaptureScript = `(function () {
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    window.__esInstallPrompt = e;
    window.dispatchEvent(new Event("es:installprompt"));
  });
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
        <script dangerouslySetInnerHTML={{ __html: nativeClientScript }} />
        <script dangerouslySetInnerHTML={{ __html: installPromptCaptureScript }} />
        <ClerkProvider>
          <QueryProvider>
            <NativeRuntime />
            {children}
            <Toaster />
          </QueryProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
