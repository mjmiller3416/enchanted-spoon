# iOS TestFlight release (no Mac)

The iOS app is the Capacitor shell `com.enchantedspoon.app` under `frontend/ios/`. It loads the hosted site. This is the owner runbook for the one App Store Connect API key, the four GitHub secrets, the App Store Connect app record, and the manual TestFlight workflow.

There is no local Mac in this setup. Signing happens on a GitHub-hosted `macos-latest` runner. Do not create a second certificate repo, and do not commit a `.p8`, a `.p12`, or a provisioning profile.

The store listing, screenshots, and subscription products stay in [MOBILE.md](MOBILE.md). This workflow uploads a build to TestFlight. It does not submit the app for App Review.

## Cost — Mitchell's OK before the first run

**Spending needs Mitchell's OK** before anyone runs this workflow on a private repository, before this repository is made private, and before `runs-on` is changed to any larger macOS runner.

Checked against GitHub's docs on 1 November 2026:

- [Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing): standard macOS (3-core M1 or 4-core Intel, SKU `actions_macos`) is **$0.062 per minute**. `macos-latest` is that runner (3-core M1). It is not the 12-core runner ($0.077) or the M2 Pro 5-core runner ($0.102).
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions): included compute is a dollar amount, **$12 on Free** and **$18 on Pro**. The same page's guide price for Linux 2-core is $0.006 per minute, so those allowances are 2,000 and 3,000 Linux minutes. One macOS minute costs `$0.062 / $0.006` = **10.33×** a Linux minute (a flat 10× would be $0.060; the extra $0.002 is the cloud platform charge already inside the $0.062 rate).
- [Billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage): standard runners, including `macos-latest`, are **free on public repositories**. Larger macOS runners are billed even on public repositories.

This repository is **public**, so a `macos-latest` run is **$0** until the repo is made private. The private-repo numbers below are what it would cost.

A normal run is about **20 minutes** (often 15–25 after the Swift packages are cached by the runner image; the first run can reach about 35 minutes while packages download). The workflow does not wait for Apple's TestFlight processing, so that queue is not billed.

| | Free (private repo) | Pro (private repo) |
| --- | --- | --- |
| Included compute | $12 (2,000 Linux minutes) | $18 (3,000 Linux minutes) |
| macOS minutes that allowance covers, if nothing else runs | 12 / 0.062 ≈ **194 minutes** | 18 / 0.062 ≈ **290 minutes** |
| One 20-minute build | 20 × $0.062 = **$1.24** (about 207 Linux minutes) | same **$1.24** |
| About 10 builds in a month (200 minutes) | **$12.40**. That is the whole Free allowance plus about **$0.40** over, and only if iOS is the only Actions usage | **$12.40 of $18**, about **$5.60** left if iOS is the only Actions usage |

A 35-minute first run is about **$2.17**. Ten such runs would be about **$21.70**, which is over both allowances. Plan on the 20-minute figure, and still get Mitchell's OK before turning the repo private.

The existing Linux CI workflow is free while the repo is public. On a private repo it draws from the same $12 or $18, so the headroom above is smaller than the iOS-only math.

## Signing approach

Xcode automatic signing with Apple's cloud-managed distribution certificate.

`xcodebuild` is called with:

- `-allowProvisioningUpdates`
- `-authenticationKeyPath` (the `.p8` written from the GitHub secret, then deleted)
- `-authenticationKeyID`
- `-authenticationKeyIssuerID`

The archive uses automatic signing for `com.enchantedspoon.app` and the share extension `com.enchantedspoon.app.share`. The export step re-signs for App Store distribution. Apple holds the distribution private key. It is not a GitHub secret and it is not in the repo.

**fastlane match is the option that was not taken.** Match stores the distribution private key in a private git repo. That adds a second repository, a git credential, and `MATCH_PASSWORD`, and it still needs this same API key. The owner has no Mac to babysit that repo. Cloud signing needs the four secrets below and nothing else.

One caveat: the archive can still create an Apple Development certificate on that runner so the archive has a signature. The private key for that development certificate dies with the runner. Export then uses the cloud distribution certificate, which is reused. If the account later hits Apple's development-certificate cap, revoke old **Apple Development** certificates in [Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources/certificates/list). Do not revoke the cloud **Apple Distribution** certificate unless you intend to.

The App Store Connect API key is not the APNs push key in [MOBILE.md](MOBILE.md). The push key cannot upload builds. This API key cannot send pushes.

## 1. Create the one API key

The account holder needs an active Apple Developer Program membership. This is done in a browser.

1. Sign in at [App Store Connect](https://appstoreconnect.apple.com).
2. **Users and Access → Integrations → App Store Connect API**.
3. Copy the **Issuer ID** at the top of that page. It is a UUID. It is per team, not per key. This becomes `APP_STORE_CONNECT_ISSUER_ID`.
4. Open **Team Keys**. Do not create an Individual key. An Individual key is tied to one person and stops working if that person's access changes.
5. Generate a key. Name it `GitHub Actions iOS`. Role: **Admin**.
6. Download the `.p8` once. Apple does not offer it again. If the download is lost, revoke that key and create another. Do not email the file.

**Admin is the role.** The workflow asks Xcode to create and refresh certificates and profiles (`-allowProvisioningUpdates`) and to upload the build. App Manager can upload a build but cannot manage certificates. Developer cannot create the distribution signing this pipeline uses. One Team key with Admin covers both, which is why there is only one key.

Also copy the **Key ID** from the keys table (10 characters). That is `APP_STORE_CONNECT_API_KEY_ID`.

## 2. Add the four GitHub secrets

Repository → **Settings → Secrets and variables → Actions → New repository secret**.

| Secret | Value |
| --- | --- |
| `APP_STORE_CONNECT_API_KEY_ID` | Key ID from the keys table. 10 characters. |
| `APP_STORE_CONNECT_ISSUER_ID` | Issuer ID from the top of the App Store Connect API page. |
| `APP_STORE_CONNECT_API_KEY_P8` | Base64 of the `.p8` file. One line, no quotes. |
| `APPLE_TEAM_ID` | Team ID from [developer.apple.com/account](https://developer.apple.com/account) → Membership details. 10 characters. It is not the Issuer ID. |

No other secrets. There is no Apple ID password, no app-specific password, no `.p12`, and no match password.

On Windows, in PowerShell, from the folder that contains the download (the owner has no Mac):

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$HOME\Downloads\AuthKey_XXXXXXXXXX.p8"))
```

Replace the filename with the real `AuthKey_….p8`. Copy the single line of output into `APP_STORE_CONNECT_API_KEY_P8`. Do not use `Get-Content`; that can change the bytes.

On Linux:

```bash
base64 -w 0 AuthKey_XXXXXXXXXX.p8
```

Then delete the `.p8` from Downloads. Keep one offline copy in a password manager or on a disk that is not the git repo. `*.p8` is gitignored under `frontend/ios/`. If a `.p8` is ever committed, revoke the key in App Store Connect and create a new one. Do not paste the key into a pull request or a chat.

A multiline paste of the PEM also works if the secret contains `-----BEGIN PRIVATE KEY-----`. Base64 is the form to store.

## 3. Create the App IDs

Do this in the browser before the first workflow run, so the archive does not spend a macOS job discovering that the ids are missing. [Identifiers](https://developer.apple.com/account/resources/identifiers/list) → **+** → App IDs → App.

| Description | Bundle ID | Capability |
| --- | --- | --- |
| Enchanted Spoon | `com.enchantedspoon.app` | Push Notifications. In-App Purchase before you test subscriptions. |
| Enchanted Spoon Share | `com.enchantedspoon.app.share` | None. |

The share extension is part of the same archive. It does not get its own App Store Connect app.

Release builds use `frontend/ios/App/App/App.release.entitlements` (`aps-environment` = `production`). Debug stays on `App.entitlements` (`development`).

## 4. Create the App Store Connect app record

[App Store Connect](https://appstoreconnect.apple.com) → **Apps → + → New App**.

| Field | Value |
| --- | --- |
| Platforms | iOS |
| Name | Enchanted Spoon |
| Primary language | English |
| Bundle ID | `com.enchantedspoon.app` (the App ID from the step above) |
| SKU | `enchanted-spoon-ios` |
| User access | Full access |

You do not need screenshots or a description to upload a TestFlight build. You do need this record. The API key cannot create it.

The account holder also has to open **Business → Agreements** and accept the Paid Applications agreement until it says Active. Subscriptions require it, including for TestFlight. The API key cannot accept an agreement.

## 5. Run the workflow

`.github/workflows/ios-release.yml` is `workflow_dispatch` only. It does not run on push or on pull requests. Merging it does not start a runner. GitHub only shows the Run button after the workflow file is on the default branch (`main`).

1. Get Mitchell's OK if the repo is private, or if you are about to make it private.
2. Actions → **iOS TestFlight** → **Run workflow**.
3. Branch: `main`.
4. Version: leave empty to keep `1.0` from the Xcode project, or type `1.0` / `1.2.0` to override `MARKETING_VERSION` for that run.
5. Run.

What the job does:

1. Fails immediately if any of the four secrets is missing.
2. Installs fastlane and checks the API key against App Store Connect (this fails before the Xcode archive if the app record or the key is wrong).
3. `npm ci` in `frontend/`.
4. Checks the web asset `frontend/mobile/www/index.html`, then `npx cap sync ios` with `CAPACITOR_SERVER_URL=https://enchantedspoon.app`. The Next.js production build is not inside the IPA. The WebView loads the hosted site. `frontend/mobile/www` is the fallback page Capacitor copies in.
5. Archives the shared scheme `App` (Release) and uploads the IPA to TestFlight.

The build number is the greater of (latest TestFlight build for that version + 1) and `GITHUB_RUN_NUMBER`. Failed runs still advance the run number, so a retry does not reuse a build number. Example: TestFlight is at 12 and this run is number 3 → build 13. TestFlight has no builds and this run is number 15 → build 15.

The job stops when the upload is accepted. Apple still processes the binary for several minutes. That wait is not billed. When it finishes, the build is under **TestFlight → iOS Builds**. Add internal testers in the browser (TestFlight → Internal Testing). The workflow does not add testers and does not submit for Beta App Review or App Review.

`frontend/ios` is a Swift package project (`App/CapApp-SPM`). There is no Podfile. `cap sync` does not run `pod install`.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `Missing GitHub Actions secret` | Add the four secrets in section 2. The archive does not start. |
| `APP_STORE_CONNECT_API_KEY_P8 is not a base64-encoded .p8` | The secret is not the base64 of the file. Re-run the PowerShell line in section 2. Do not base64 the text twice. |
| `401`, `403`, `not authorized`, `Invalid JWT` | Key ID, Issuer ID, and `.p8` are not a matching set, or the key was revoked. Create one new Team key and replace all three secrets together. |
| `No Accounts` or `No profiles for 'com.enchantedspoon.app'` | The API key did not reach `xcodebuild`. Confirm the key role is Admin (not App Manager) and `APPLE_TEAM_ID` is the team that owns the bundle id. |
| `Could not read TestFlight builds` / bundle id not found on upload | The App Store Connect app record from section 4 does not exist yet, or the bundle id does not match `com.enchantedspoon.app`. |
| Agreement / "paid apps" / contracts error | Account holder: Business → Agreements. The Paid Applications agreement has to be Active. |
| `aps-environment` or Push Notifications profile error | Enable Push Notifications on the App ID `com.enchantedspoon.app`. Release uses production. |
| Share extension profile error | Register `com.enchantedspoon.app.share` (section 3). |
| `bundle version must be higher` or `Redundant Binary Upload` | Re-run the workflow. It reads the latest TestFlight build and increments. Do not upload a second binary with the same version and build by hand in between. |
| `maximum number of certificates` | Revoke old Apple Development certificates created by Xcode. Leave the cloud Apple Distribution certificate. |
| Build sits on Missing Compliance | It should not. `ITSAppUsesNonExemptEncryption` is false (HTTPS only) and the upload sends the same answer. If it still asks, answer the export question in TestFlight: no non-exempt encryption. |
| Package resolution / `capacitor-swift-pm` failed | Re-run. The runner needs to reach GitHub to fetch the Swift package. |
| Export warns that `app-store` is deprecated | Expected. fastlane 2.241 writes `app-store`, and current Xcode still accepts it as the alias of `app-store-connect`. The upload can continue. |
| Workflow is not listed under Actions | The file is not on `main` yet. Merge first. That merge does not start a build. |
| Job was cancelled or hit the 45-minute timeout | A cancelled macOS job is still billed for the minutes it used on a private repo. Do not start a second run until the first one has finished (`cancel-in-progress` is off on purpose). |

Do not switch this workflow to `macos-latest-xl`, `macos-14-xl`, or any larger runner to make it faster. Those minutes are billed even while the repository is public.
