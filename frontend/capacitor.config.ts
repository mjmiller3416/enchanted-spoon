import type { CapacitorConfig } from "@capacitor/cli";

/**
 * The native apps load the hosted Next.js app. A static export cannot
 * replace it: the site uses the standalone server output, Clerk middleware,
 * and dynamic routes. `CAPACITOR_SERVER_URL` overrides the baked-in URL at
 * `cap sync` time (for example http://10.0.2.2:3000 from an Android emulator).
 */
const serverUrl = process.env.CAPACITOR_SERVER_URL || "https://enchantedspoon.app";

const config: CapacitorConfig = {
  appId: "com.enchantedspoon.app",
  appName: "Enchanted Spoon",
  webDir: "mobile/www",
  server: {
    url: serverUrl,
    cleartext: serverUrl.startsWith("http://"),
    androidScheme: "https",
    // OAuth and Clerk stay inside the WebView. Other origins are opened in
    // the system browser by NativeRuntime.
    allowNavigation: [
      "enchantedspoon.app",
      "*.enchantedspoon.app",
      "*.clerk.accounts.dev",
      "*.clerk.com",
      "accounts.google.com",
      "*.google.com",
      "*.googleapis.com",
      "appleid.apple.com",
      "*.apple.com",
    ],
  },
  ios: {
    contentInset: "automatic",
    scheme: "enchantedspoon",
    appendUserAgent: "EnchantedSpoonApp",
  },
  android: {
    appendUserAgent: "EnchantedSpoonApp",
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: "#F8F9FA",
      showSpinner: false,
    },
  },
};

export default config;
