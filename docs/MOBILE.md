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
- The first free trial on the account (Stripe, App Store, or Play) is recorded on the user. A later trial does not grant Pro (`store_status = trial_suppressed`, or a Stripe trial left at tier `free`). Do not also put a trial on the Stripe Price. Checkout adds `trial_period_days` only when the account has not consumed a trial. Set `STRIPE_PRICE_ID_PRO` to the $6.99/mo price and `STRIPE_PRICE_ID_PRO_ANNUAL` to the $49.99/yr price.
- Web checkout allows promotion codes so **FOUNDER30** can be entered there. There is no store offer code.

The paywall (native shell) shows the annual plan selected, the trial timeline, the price and the date the first charge happens, a Close button, Restore purchases, and links to `/privacy` and `/terms`.

### Founding price (FOUNDER30)

Web only. The native UI mentions it only where the store currently allows a link to a web purchase:

- **Website:** the pricing page shows the code.
- **iOS, United States storefront:** [Guideline 3.1.1(a)](https://developer.apple.com/app-store/review/guidelines/#in-app-purchase) allows buttons and external links to other purchase methods on the United States storefront without a StoreKit External Purchase Link entitlement. The link is shown only after RevenueCat reports storefront `US` or `USA`, and it opens in the system browser. Other storefronts do not see it. This build does not request the non-US entitlement.
- **Android:** [External Content Links](https://developer.android.com/google/play/billing/externalcontentlinks) requires Play Console enrollment, a registered destination, and the Play Billing link API (information screen, then `launchExternalLink`) before any link. This app is not enrolled, so the founding price is not mentioned on Android.

### Read-only accounts

Accounts created on or before 2026-10-31 keep the full free plan through 2027-03-31 23:59:59 UTC. After that they are `access_mode: "read_only"`: they can view and export, delete the account, and subscribe, and other writes return 403 `account_read_only`. The app shows a banner and the paywall. Pro, admin, and granted access stay full. Accounts created after the cutoff stay on the current metered free plan; they are not flipped to read-only on that date.

## Release builds

Do this on a Mac for iOS. Android can be built on macOS or Linux with the Android SDK. This repo does not contain signing keys, store listings, or a submission.

### iOS (Xcode archive)

1. Apple Developer account, App ID `com.enchantedspoon.app`, and a distribution certificate plus an App Store provisioning profile.
2. `cd frontend && npm ci && npx cap sync ios`
3. `npx cap open ios`
4. In Xcode, select the App target. Signing & Capabilities: team, bundle id `com.enchantedspoon.app`. Add the In-App Purchase capability before shipping purchases.
5. Associated Domains / universal links are not configured yet. Add them when Clerk email links should open the app.
6. Product → Archive. Distribute to App Store Connect. Do not upload until the listing in the checklist below is ready.

`pod install` runs on the Mac as part of `cap sync` when CocoaPods is installed. Pods are not committed.

### Android (AAB)

1. Play Console app with application id `com.enchantedspoon.app`.
2. Create an upload keystore and keep it out of git. `android/local.properties` (SDK path) is gitignored.
3. `cd frontend && npm ci && npx cap sync android`
4. Open `android/` in Android Studio, or:

```bash
cd frontend/android
./gradlew bundleRelease
```

5. Sign the AAB with the upload key (`Play App Signing` is the usual choice). The artifact is `android/app/build/outputs/bundle/release/app-release.aab`.
6. Upload to the Play Console internal testing track. Do not promote to production until the checklist is done.

A `google-services.json` is not required for this shell.

## Submission checklist

Do not create the store records or submit as part of development. When you do:

### Both stores

- [ ] Subscription group with `com.enchantedspoon.app.pro.monthly` ($6.99) and `com.enchantedspoon.app.pro.annual` ($49.99), 7-day free trial intro, same entitlement `pro` in RevenueCat.
- [ ] RevenueCat project, iOS and Android public SDK keys, secret API key, webhook `https://<api>/api/webhooks/revenuecat` with the authorization header. Then set `NATIVE_IAP_ENABLED=true` and the `NEXT_PUBLIC_REVENUECAT_*` keys and redeploy the web app **before** sending sandbox purchases.
- [ ] Stripe prices updated to $6.99/mo and $49.99/yr (`STRIPE_PRICE_ID_PRO`, `STRIPE_PRICE_ID_PRO_ANNUAL`). No trial configured on the Price. FOUNDER30 coupon created in Stripe only.
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

- Trial usage caps of 3/25/20/5 (the existing free and Pro meters stay as they are).
- Onboarding: three questions, pick or import three recipes, auto-fill the week, aisle-sorted list, under three minutes, paywall after the list.
- Day-5 trial reminder (push and email) and the days-left banner.
- Push permission after trial start, and local notifications on days 1–6.
- Home checklist for days 0–6.
- Funnel analytics.
- Store offer codes. FOUNDER30 stays web-only.
- Cancel-flow survey and annual save offer.
- Referral deep links.
- Read-only immediately on lapse for accounts created after 2026-10-31. Existing free accounts do become read-only after 2027-03-31.
- Review prompt, paywall A/B test, win-back offers, home-screen widget.

## Known risks

- **Guideline 4.2.** A shell that only loads a website can be rejected for minimum functionality. The paywall, restore, and native purchase path are the store-specific behavior; the rest of the product is the hosted app. Review may still ask for more native UI.
- **Google sign-in inside the WebView.** Google often blocks OAuth with `disallowed_useragent` in WKWebView and the Android WebView. Email and password Clerk sign-in is the path to verify first. A system-browser handoff back through `enchantedspoon://` is not built.
- **Cookies and ITP.** First-party cookies on the hosted origin are the intended session. If Clerk is ever served from a different site inside the WebView, the session will not stick.
- **`server.url` requires the network.** There is no offline copy of the app.
- **Store products and RevenueCat do not exist yet.** With the flag off, the paywall still renders and purchase or restore reports that in-app purchases are not turned on. Do not submit until a sandbox purchase completes.
- **Price ids in Stripe** still have to be changed in the dashboard. The UI now shows $6.99 and $49.99. Checkout charges whatever price those ids point at.
