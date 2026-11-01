# Enchanted Spoon on iOS and Android

The native apps are a Capacitor shell (`com.enchantedspoon.app`) around the hosted Next.js site. They are not a static export of the frontend.

## Why the shell loads the server

`frontend/next.config.ts` builds a standalone server for Railway. The app also depends on Clerk (`frontend/src/proxy.ts`), server-rendered pages, and dynamic routes such as `/recipes/[id]`. `output: "export"` would drop all of that. Capacitor's `server.url` loads `https://enchantedspoon.app` (override with `CAPACITOR_SERVER_URL` at `npx cap sync` time) inside a WebView.

What that means in practice:

- **SSR and API routes** keep running on the web server. The shell does not bundle them.
- **Auth cookies** are first-party. The WebView's document origin is the hosted site, so Clerk's session cookies are set for that host, not for a `capacitor://` origin. `androidScheme` is `https`.
- **External links** (a recipe's source URL, and the founding-price link) are opened in the system browser by `NativeRuntime`. Same-origin navigation stays in the WebView. Clerk and the OAuth hosts in `capacitor.config.ts` `allowNavigation` may stay in the WebView.
- **Stripe Checkout is not offered in the shell.** The web app sends `X-Enchanted-Spoon-Client: native-ios` or `native-android`, and the API refuses checkout and portal sessions for that header. The purchase UI is StoreKit 2 / Play Billing.

`frontend/mobile/www` is only the fallback `webDir` Capacitor requires. With `server.url` set, it is not the app people use.

## Local run

From `frontend/`:

```bash
npm install
npm run dev
```

Point a simulator at that server and sync:

```bash
# iOS simulator, from the host machine
CAPACITOR_SERVER_URL=http://localhost:3000 npx cap sync
npx cap open ios

# Android emulator (10.0.2.2 is the host loopback)
CAPACITOR_SERVER_URL=http://10.0.2.2:3000 npx cap sync
npx cap open android
```

`http://` is cleartext and is only for that local URL. Production sync uses `https://enchantedspoon.app`.

The backend still has to be running and reachable at `NEXT_PUBLIC_API_URL`. Clerk has to allow the origin you load.

Copy `frontend/.env.example` for the public flags. Leave `NEXT_PUBLIC_NATIVE_IAP_ENABLED` unset or `false` until RevenueCat keys exist. Those flags are compiled into the **hosted** web bundle, because that is the code the WebView runs. Changing them means rebuilding and redeploying the frontend, not only the native binary.

## Icons and splash

Source art is `frontend/assets/` (1024px icons, 2732px splash). Icon background `#1A1A1A`. Splash light `#F8F9FA`, dark `#1A1A1A`.

```bash
npm run assets:generate
npx cap sync
```

Web icons: `src/app/favicon.ico`, `icon.png`, `icon.svg`, `apple-icon.png`, `opengraph-image.png`, and `public/icon-192.png`, `icon-512.png`, `icon-maskable-512.png` (maskable purpose in `src/app/manifest.webmanifest`). The in-app mark is `public/logo.svg` and `components/layout/Logo.tsx`.

`@capacitor/assets` 4.0 generates the adaptive icon and splashes from `icon-only`, `icon-foreground`, `icon-background`, and the splash files. It does not read `icon-monochrome.png`. That file stays in `frontend/assets/` and is also copied to `android/app/src/main/res/drawable/ic_launcher_monochrome.png` and referenced from the adaptive icon XML. Running `npm run assets:generate` rewrites that XML and drops the monochrome layer; put the `<monochrome>` node back afterward.

## In-app purchase

**RevenueCat** (`@revenuecat/purchases-capacitor`) is the store client. One SDK covers StoreKit 2 and Play Billing, identifies the customer as our numeric user id, and sends server notifications. A hand-rolled StoreKit plugin would duplicate receipt validation we would then have to keep in sync with Stripe.

Product ids (change only in both env files if the store records differ):

| Plan | Price (US) | Product id |
| --- | --- | --- |
| Pro monthly | $6.99 | `com.enchantedspoon.app.pro.monthly` |
| Pro annual | $49.99 | `com.enchantedspoon.app.pro.annual` |

Both are auto-renewable, in one subscription group, with a 7-day free-trial introductory offer. Entitlement id: `pro`.

Server:

- `NATIVE_IAP_ENABLED` gates applying webhooks and the post-purchase sync. While it is false, `POST /api/webhooks/revenuecat` checks the authorization header and then returns `result: "disabled"` without granting Pro. Point RevenueCat at the webhook only after the flag is on.
- `REVENUECAT_WEBHOOK_AUTHORIZATION` is the full `Authorization` value from the RevenueCat dashboard.
- `REVENUECAT_SECRET_API_KEY` is the secret key used by `POST /api/billing/store/sync`. The app cannot grant itself Pro; the server reads RevenueCat.
- Stripe columns and store columns are separate. `has_pro_access` is true when either is current.
- The first free trial on the account (Stripe, App Store, or Play) is recorded on the user. A later store trial does not grant Pro (`store_status = trial_suppressed`). A later Stripe trial is left at tier `free` when the webhook reports `trialing`.
- Web checkout, trial length, trial usage caps, and which Stripe price is charged are **not** implemented here. That work is the cost/trial change (`bc-ced52f02`). Production already has `STRIPE_PRICE_PRO_MONTHLY_V2` ($6.99/mo) and `STRIPE_PRICE_PRO_ANNUAL_V2` ($49.99/yr). This shell does not read those variables and does not add a second checkout implementation.

The paywall (native shell) shows the annual plan selected, the trial timeline, the price and the date the first charge happens, a Close button, Restore purchases, and links to `/privacy` and `/terms`.

### Founding price (FOUNDER30)

Web only. The native UI mentions it only where the store currently allows a link to a web purchase:

- **Website:** the pricing page shows the code until the shared sunset below.
- **iOS, United States storefront:** [Guideline 3.1.1(a)](https://developer.apple.com/app-store/review/guidelines/#in-app-purchase) allows buttons and external links to other purchase methods on the United States storefront without a StoreKit External Purchase Link entitlement. The link is shown only after RevenueCat reports storefront `US` or `USA`, and it opens in the system browser. Other storefronts do not see it. This build does not request the non-US entitlement.
- **Android:** [External Content Links](https://developer.android.com/google/play/billing/externalcontentlinks) requires Play Console enrollment, a registered destination, and the Play Billing link API (information screen, then `launchExternalLink`) before any link. This app is not enrolled, so the founding price is not mentioned on Android.

### Read-only accounts

Who is free, who is read-only, and who has no free AI allowance is owned by #210. This shell does not enforce that policy. It reads the account payload #210 returns (`is_read_only`, `usage_tier`, `free_tier_sunset_at`) and, in the native app, sends an AI action that the API rejects to the 7-day trial paywall.

The shared setting is `LEGACY_FREE_CUTOFF` (ISO 8601, naive values are Eastern Time). It is the coordinated release instant. Leave it unset until that deploy. Accounts created before it keep the free plan until `FREE_TIER_SUNSET_AT` (default March 31, 2027, 11:59 PM America/New_York). Accounts created at or after it get no free AI allowance: any AI action starts the 7-day card trial, and recipes, planning, and shopping stay free. `FOUNDER_OFFER_ENDS_AT` is the same default instant for the web founding code. Do not add a second name for these.

## Push notifications

Permission is requested only after a trial starts (`subscription_status` or `store_status` is `trialing`). The app then registers the device token with `POST /api/devices`. Starting a trial schedules two nudges, on day 5 and day 6. A cron calls `POST /api/internal/push/dispatch` with header `X-Push-Dispatch-Key: $PUSH_DISPATCH_SECRET`. Without APNs or FCM credentials the nudges stay queued.

Approved store ids: `com.enchantedspoon.app.pro.monthly`, `com.enchantedspoon.app.pro.annual`, entitlement `pro`.

### APNs

1. Apple Developer → Keys → create an Apple Push Notifications service key (`.p8`). Note the Key ID and your Team ID.
2. Enable Push Notifications on the App ID `com.enchantedspoon.app`. The Xcode target already points at `App/App.entitlements` (`aps-environment`). Use `development` for sandbox and switch that value to `production` for App Store builds.
3. On the API service set:
   - `APNS_KEY_ID`
   - `APNS_TEAM_ID`
   - `APNS_AUTH_KEY` (the `.p8` contents; newlines may be written as `\n`)
   - `APNS_BUNDLE_ID=com.enchantedspoon.app`
   - `APNS_USE_SANDBOX=true` until the build is a production App Store build
   - `PUSH_DISPATCH_SECRET` (any long random string)

### FCM

1. Create a Firebase project and add an Android app with package `com.enchantedspoon.app`.
2. Download `google-services.json` into `frontend/android/app/` when you are ready to ship push. It is gitignored. CI reads it from the `GOOGLE_SERVICES_JSON` secret. See [ANDROID_RELEASE.md](ANDROID_RELEASE.md).
3. Cloud Messaging → manage service accounts, or use the legacy server key if the project still offers it. Set `FCM_SERVER_KEY` on the API service to that key. The sender posts to `https://fcm.googleapis.com/fcm/send`.
4. The app requests `POST_NOTIFICATIONS` at runtime after the trial starts.

## Share a recipe link

iOS: the ShareExtension target (`com.enchantedspoon.app.share`) accepts a URL or plain text and opens `enchantedspoon://import?url=`. Android: the activity accepts `ACTION_SEND` of `text/plain` and the `enchantedspoon` scheme. The hosted app opens the recipe wizard on URL import and calls `POST /api/ai/recipe-import` (the same flow as pasting a link). TikTok and Instagram shares are ordinary text that contain an `https` URL.

## Offline grocery list

The latest shopping list is stored in `localStorage`. When the device is offline, the list screen shows that copy. Checking an item off updates the copy immediately and queues the write. Coming back online replays the queue through the existing shopping update API.

## Google sign-in

In the native shell, Continue with Google opens the system browser (Safari View Controller or Chrome Custom Tabs), not the WebView. Clerk must allow the redirect `enchantedspoon://sso-callback`. The app loads that callback into `/sso-callback` on the hosted origin so the existing Clerk handoff can finish. The website still uses the in-page redirect.

## Release builds

Do this on a Mac for iOS. Android can be built on macOS or Linux with the Android SDK. This repo does not contain signing keys, store listings, or a submission. The Android upload key, signed AAB, and Play internal/closed test are in [ANDROID_RELEASE.md](ANDROID_RELEASE.md).

### iOS (Xcode archive)

1. Apple Developer account, App ID `com.enchantedspoon.app`, and a distribution certificate plus an App Store provisioning profile.
2. `cd frontend && npm ci && npx cap sync ios`
3. `npx cap open ios`
4. In Xcode, select the App target. Signing & Capabilities: team, bundle id `com.enchantedspoon.app`. Add the In-App Purchase capability before shipping purchases.
5. Associated Domains / universal links are not configured yet. Add them when Clerk email links should open the app.
6. Product → Archive. Distribute to App Store Connect. Do not upload until the listing in the checklist below is ready.

`pod install` runs on the Mac as part of `cap sync` when CocoaPods is installed. Pods are not committed.

### Android (AAB)

Follow [ANDROID_RELEASE.md](ANDROID_RELEASE.md). Short form, from `frontend/`:

```bash
npm ci
CAPACITOR_SERVER_URL=https://enchantedspoon.app npx cap sync android
cd android
./gradlew bundleRelease
```

`bundleRelease` signs with `keystore.properties` or `ANDROID_KEYSTORE_PATH`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, and `ANDROID_KEY_PASSWORD`, and writes `app/build/outputs/bundle/release/app-release.aab`. `versionName` is `package.json`. `versionCode` is `ANDROID_VERSION_CODE` or `GITHUB_RUN_NUMBER`. The upload key stays out of git. `com.android.vending.BILLING` is merged from the Play Billing library that `@revenuecat/purchases-capacitor` depends on.

`google-services.json` is not required for the shell to load the site. It is required for FCM, it is gitignored, and the release workflow injects it from `GOOGLE_SERVICES_JSON`.

## Submission checklist

Do not create the store records or submit as part of development. When you do:

### Both stores

- [ ] Subscription group with `com.enchantedspoon.app.pro.monthly` ($6.99) and `com.enchantedspoon.app.pro.annual` ($49.99), 7-day free trial intro, same entitlement `pro` in RevenueCat.
- [ ] RevenueCat project, iOS and Android public SDK keys, secret API key, webhook `https://<api>/api/webhooks/revenuecat` with the authorization header. Then set `NATIVE_IAP_ENABLED=true` and the `NEXT_PUBLIC_REVENUECAT_*` keys and redeploy the web app **before** sending sandbox purchases.
- [ ] Stripe monthly and annual prices stay on `STRIPE_PRICE_PRO_MONTHLY_V2` and `STRIPE_PRICE_PRO_ANNUAL_V2` (already set in Railway production). Checkout, the 7-day card trial, trial caps, `LEGACY_FREE_CUTOFF`, `FREE_TIER_SUNSET_AT`, and `FOUNDER_OFFER_ENDS_AT` are #210, not this shell.
- [ ] Privacy policy URL `https://enchantedspoon.app/privacy` and Terms of Use URL `https://enchantedspoon.app/terms` (the terms include the subscription disclosure).
- [ ] Support URL and `info@enchantedspoon.app`.
- [ ] Screenshots, description, age rating, and a review account Clerk can sign into. The reviewer must be able to reach the paywall from Settings → Plan & Billing and from a Pro-gated action, close it, and tap Restore purchases.
- [ ] Confirm a US sandbox purchase, a restore, a second trial on the same account (must not extend Pro), and a lapsed or post-2027-03-31 free account showing the view-only banner.

### App Store Connect

- [ ] Bundle ID `com.enchantedspoon.app`. In-App Purchase capability on the App ID.
- [ ] Subscription localization: name “Enchanted Spoon Pro”, durations, prices, and the 7-day trial.
- [ ] App privacy nutrition labels (account, recipes, purchases).
- [ ] Review notes: the app loads the hosted site; sign-in is Clerk; subscriptions are in-app; Stripe is not shown; the founding offer appears only on the US storefront.
- [ ] Guideline 3.1.2 metadata: privacy policy and EULA links in the description or the EULA field, matching the in-app links.
- [ ] Export compliance and encryption questionnaire (HTTPS only).

### Play Console

- [ ] Application id `com.enchantedspoon.app`.
- [ ] Subscriptions created and activated. License testers added.
- [ ] Data safety form, content rating, and store listing.
- [ ] Do not enroll in External Content Links or show FOUNDER30 until the Play Billing information screen and transaction reporting are implemented. The current build does not link out on Android.
- [ ] Internal testing track first. AAB uploaded with Play App Signing.

## Deferred from the trial build list

Not in this change:

- Trial usage caps, checkout, and who has a free AI allowance. That policy is #210 (`LEGACY_FREE_CUTOFF`, `FREE_TIER_SUNSET_AT`, `FOUNDER_OFFER_ENDS_AT`). This shell does not grant new accounts a metered free AI plan.
- Onboarding: three questions, pick or import three recipes, auto-fill the week, aisle-sorted list, under three minutes, paywall after the list.
- Email half of the day-5 reminder, and the days-left banner. Remote push for day 5 and day 6 is scheduled here.
- Local notifications on days 1–4.
- Home checklist for days 0–6.
- Funnel analytics.
- Store offer codes. FOUNDER30 stays web-only.
- Cancel-flow survey and annual save offer.
- Referral deep links.
- Read-only enforcement after the sunset. #210 owns that. This app only displays `is_read_only` when that API sends it.
- Review prompt, paywall A/B test, win-back offers, home-screen widget.

## Known risks

- **Guideline 4.2.** Push, share-in, and the offline grocery list are the native surface. They still need a device pass before submission.
- **Google sign-in** uses the system browser and `enchantedspoon://sso-callback`. It fails until that URL is on the Clerk redirect allowlist, and until the dashboard's Google provider is enabled.
- **Push delivery** stays queued until `APNS_*` and `FCM_SERVER_KEY` are set. FCM's legacy server key is what this sender uses; a project that only has HTTP v1 needs that key or a follow-up sender.
- **Share extension** needs its own provisioning profile (`com.enchantedspoon.app.share`) the first time you archive.
- **Cookies and ITP.** First-party cookies on the hosted origin are the intended session. If Clerk is ever served from a different site inside the WebView, the session will not stick.
- **`server.url` requires the network** for everything except the cached grocery list.
- **Store products and RevenueCat do not exist yet.** With the flag off, purchase or restore reports that in-app purchases are not turned on.
- **Stripe price ids** `STRIPE_PRICE_PRO_MONTHLY_V2` and `STRIPE_PRICE_PRO_ANNUAL_V2` are wired by #210, not here.
