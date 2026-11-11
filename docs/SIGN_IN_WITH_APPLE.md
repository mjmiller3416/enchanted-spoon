# Sign in with Apple

App Store guideline 4.8 says an app that offers a third-party login such as Google must also offer an equivalent option. Sign in with Apple is that option. Enchanted Spoon sign-in is the custom Clerk forms in `SignInForm` and `SignUpForm`. The iOS and Android apps are Capacitor shells that load the hosted site, so this UI ships with the **frontend deploy**, not with a new IPA.

Checked against the live production Frontend API (`https://clerk.enchantedspoon.app/v1/environment`, instance `ins_3HpAGf9SQJJ6eSKnEMJhLTN99Pz`):

- Instance type is production. Home URL is `https://enchantedspoon.app`.
- Social connections: `oauth_google` only (`enabled` and `authenticatable`). There is no `oauth_apple`.
- First factors include `password`, `email_code`, and `oauth_google`.
- `native_app_settings` has no iOS app registered.

Nothing in this repo, and no change made from here, turns Apple on. A production Clerk instance rejects Apple until custom credentials from the Apple Developer portal are saved in the Clerk dashboard.

## What the app does now

**Continue with Apple** is on both the sign-in and sign-up forms, and it renders only when Clerk reports `oauth_apple` as enabled and authenticatable. The check reads Clerk's loaded environment (`__internal_environment` or `__unstable__environment`). If that object is missing, the page asks `https://<frontend-api>/v1/environment` and uses `user_settings.social.oauth_apple`.

- **Website:** Clerk redirects in the page to `/sso-callback`, the same handoff Google already uses.
- **iOS and Android shells:** the provider page opens in the system browser (`@capacitor/browser`), then Clerk returns to `enchantedspoon://sso-callback`. `NativeRuntime` loads that into `/sso-callback` on `https://enchantedspoon.app`. Google already works this way because Google rejects embedded WebViews, and Apple's web flow is built for Safari.

That is Clerk's web strategy `oauth_apple`. The client id is an Apple **Services ID**, not the app bundle id. The app does not contain a Team ID, Key ID, Services ID, or the `.p8` private key, and it must not.

No Capacitor Apple plugin and no `com.apple.developer.applesignin` entitlement were added. This flow does not call AuthenticationServices. Putting that entitlement in `App.entitlements` would make the next TestFlight archive fail code signing until the App ID capability is on the provisioning profile, and it would not make sign-in work any sooner. The system-browser button starts working on the current shell as soon as Clerk has the connection and this frontend is deployed.

### iOS fallback until Apple is really available

Google stays hidden in the iOS shell (`Capacitor.getPlatform() === "ios"`, via the `native-ios` class the shell adds before paint). Web and Android still show Continue with Google. The hide is `html.native-ios .ios-social-auth` until Apple is enabled, and `html.native-ios .ios-google-sign-in` once Apple is on the form but Google is still switched off.

Show Google on iOS again only after a real iPhone has finished Continue with Apple. On the frontend service set:

```bash
NEXT_PUBLIC_IOS_GOOGLE_SIGN_IN=true
```

`NEXT_PUBLIC_*` values are baked into the hosted bundle. Redeploy the frontend after setting the variable. Do not set it before Apple works, or the iOS app offers Google without a working Apple button.

An account that can only sign in with Google, and hits the iPhone app while Google is hidden, is told to open enchantedspoon.app in Safari or to email `info@enchantedspoon.app`.

## Who does the remaining steps

| Step | Who |
|---|---|
| Apple Developer portal (App ID, Services ID, key, Team ID, email relay) | **Mitchell Miller**, the Account Holder on `mj.miller3416@gmail.com`. Enrollment is an individual team, so he is the person who can create identifiers and keys. |
| Clerk dashboard (paste those credentials, allow the redirect) | Whoever administers production instance `ins_3HpAGf9SQJJ6eSKnEMJhLTN99Pz`. This change did not touch the dashboard. |
| Frontend env flag, after a device proves Apple works | Whoever deploys the frontend. Set `NEXT_PUBLIC_IOS_GOOGLE_SIGN_IN=true` and redeploy. |

Do not commit the `.p8`, and do not put it in the app or in GitHub Actions. It is pasted into Clerk once and stored there.

## 1. Apple Developer portal (Mitchell)

Use the Apple ID that holds the Developer Program membership. Keep a Clerk dashboard tab open at the same time (section 2) so the Return URL and the private-relay email can be copied from Clerk rather than invented.

### 1.1 App ID

1. [Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources) → Identifiers.
2. Open the App ID `com.enchantedspoon.app`. If it does not exist yet, register an App ID of type App with that bundle id (the same id the Xcode project already uses).
3. Enable the **Sign in with Apple** capability. Save.

This capability is the primary App ID for the Services ID and the key. The iOS target does not need the matching entitlement for the system-browser flow.

### 1.2 Team ID

Membership details → copy the **Team ID**. This is the Team ID field in Clerk. It is also the App ID Prefix.

### 1.3 Services ID

The Services ID is the OAuth client id. It cannot be the same string as the bundle id.

1. Identifiers → the type menu → **Services IDs** → +.
2. Description: `Enchanted Spoon Sign In`. Identifier: `com.enchantedspoon.app.signin`. Register.
3. Open the new Services ID. Enable **Sign in with Apple** → Configure.
4. Primary App ID: `com.enchantedspoon.app`.
5. Domains and Subdomains: `clerk.enchantedspoon.app` (no `https://`).
6. Return URLs: the **Return URL** copied from the Clerk Apple connection page. For this Frontend API that is `https://clerk.enchantedspoon.app/v1/oauth_callback`. If Clerk shows a different URL, use the dashboard value.
7. Next → Done → Continue → Save.

### 1.4 Sign in with Apple key

1. Keys → +.
2. Name: `Enchanted Spoon Sign in with Apple`. Enable **Sign in with Apple** → Configure → Primary App ID `com.enchantedspoon.app` → Save.
3. Continue → Register.
4. Copy the **Key ID**.
5. Download the `.p8`. Apple will not offer that download again. Keep it somewhere Mitchell controls, then paste it into Clerk (section 2). Do not email it to the repository and do not add it to git.

### 1.5 Private email relay

Apple's Hide My Email addresses only accept mail from sources registered here. This Clerk instance requires an email on every account, so skip this and relay delivery fails.

1. On the Clerk Apple connection page, copy **Email Source for Apple Private Email Relay**. It is specific to this instance and looks like `bounces+…@clkmail.enchantedspoon.app`.
2. Apple Developer → Services → **Sign in with Apple for Email Communication** → Configure.
3. Email Sources → + → paste that address → Next → Register.
4. Wait until the source shows a verified check. If it does not, wait for DNS and use Reverify SPF. Do not switch the Clerk instance off "sign up with email" to paper over a missing source.

## 2. Clerk dashboard (instance admin)

Production instances have no shared Apple credentials. Development-instance instructions do not apply to `ins_3HpAGf9SQJJ6eSKnEMJhLTN99Pz`.

1. [Clerk dashboard](https://dashboard.clerk.com) → this production instance → **SSO connections** (Configure → SSO connections).
2. Add connection → **For all users** → **Apple**.
3. Turn on **Enable for sign-up and sign-in** and **Use custom credentials**.
4. Copy the Return URL into the Services ID (section 1.3) and the Email Source into Apple's relay settings (section 1.5) before saving, if those Apple steps are not done yet.
5. Paste:
   - Apple Team ID (section 1.2)
   - Apple Services ID `com.enchantedspoon.app.signin`
   - Apple Key ID (section 1.4)
   - Apple Private Key: the full `.p8` file, including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` lines
6. Save.
7. **Paths** (or the redirect allowlist): confirm both of these are allowed. Google native sign-in already needs the custom scheme.
   - `https://enchantedspoon.app/sso-callback`
   - `enchantedspoon://sso-callback`

The website button and the iOS button both call `oauth_apple`. A native AuthenticationServices sheet (`oauth_token_apple`) is a different setup and is not what this app calls. Do not add a Bundle ID on the Apple connection unless Clerk's current form still asks for one; current Clerk docs put native bundle ids on the Native applications page, and this shell does not use that flow.

## 3. Prove it, then allow Google on iOS

1. Deploy the frontend that contains this change, if it is not on `https://enchantedspoon.app` yet. The shell loads that site, so no Xcode archive is required for the button.
2. On the website, open `/sign-in` and `/sign-up`. **Continue with Apple** is above **Continue with Google**. Finish a sign-up and a sign-in, including Hide My Email if you can. A failure is an `oauth_callback.failed` event in the Clerk application logs.
3. On an iPhone build, the same button opens Safari and returns to the app signed in. Google is still absent.
4. Set `NEXT_PUBLIC_IOS_GOOGLE_SIGN_IN=true` on the frontend service and redeploy. iOS then shows Apple and Google. Web and Android are unchanged either way.

## If review asks for the native Apple sheet

Only then:

1. Mitchell enables Sign in with Apple on the App ID (already required above) and the next archive's provisioning profile must include it.
2. Add `com.apple.developer.applesignin` = `Default` to both `frontend/ios/App/App/App.entitlements` and `App.release.entitlements`.
3. Add a Capacitor 8 plugin such as `@capawesome/capacitor-apple-sign-in`, run `npx cap sync ios`, and ship a new IPA. On iOS the plugin returns an identity token whose audience is `com.enchantedspoon.app`.
4. In Clerk, register a native iOS application with App ID Prefix (the Team ID) and bundle id `com.enchantedspoon.app`, and exchange the token with strategy `oauth_token_apple`.

The production Apple social connection (Services ID and key) is still required before Clerk enables Apple at all. The system-browser path above does not wait on that extra native registration.
