# Android release and Play closed testing

The Android app is the Capacitor shell `com.enchantedspoon.app` under `frontend/android/`. It loads the hosted site. This document is the owner runbook for the upload key, the signed AAB, and the Play internal then closed test.

Agents working on this repo do not have a Play Console account of their own. Every Play Console step is done by the owner, or in a browser where the owner is already signed in. Do not register a Play developer account from an agent, and do not turn on a paid GitHub runner. The release workflow uses the free `ubuntu-latest` runner and runs only when someone starts it by hand.

The Capacitor shell landed in [#209](https://github.com/mjmiller3416/enchanted-spoon/pull/209). This runbook is the upload-key and Play testing follow-up.

## 1. Generate the upload key

On the owner's machine, with JDK 21 or newer:

```bash
scripts/android/generate-upload-keystore.sh
```

The script asks for a keystore password and a key password. The prompts do not echo. It writes three files outside the repo, in `~/enchanted-spoon-secrets/` unless another absolute directory is passed:

| File | Purpose |
| --- | --- |
| `upload-keystore.jks` | Upload key. RSA 4096, 10,000-day validity, alias `upload`, PKCS12. |
| `upload-keystore.jks.base64` | Same key, for GitHub secret `ANDROID_KEYSTORE_BASE64`. |
| `keystore.properties` | Local Gradle signing. Not for CI. |

The script prints the certificate SHA-1 and SHA-256. Those are the upload-key fingerprints. It also prints the backup steps: both passwords go in a password manager, and the `.jks` (plus the base64 copy) goes on an offline disk or USB that is not the only copy. Play App Signing can reset a lost upload key later, but that is a support process and it blocks updates until it finishes.

The script refuses to write inside the git repo. `*.jks`, `*.keystore`, `*.jks.base64`, `*.keystore.base64`, and `keystore.properties` are gitignored in case a path is wrong. `frontend/android/app/google-services.json` is gitignored too.

For a local release build, symlink the properties file (it is gitignored):

```bash
ln -sfn ~/enchanted-spoon-secrets/keystore.properties frontend/android/keystore.properties
```

Gradle reads that file, or these environment variables if they are set (they win over the file):

- `ANDROID_KEYSTORE_PATH`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS` (defaults to `upload`)
- `ANDROID_KEY_PASSWORD`

`versionName` comes from `frontend/package.json`. `versionCode` is `ANDROID_VERSION_CODE`, otherwise `GITHUB_RUN_NUMBER`, otherwise `1`.

## 2. GitHub secrets

Repository → Settings → Secrets and variables → Actions → New repository secret.

| Secret | Required | Value |
| --- | --- | --- |
| `ANDROID_KEYSTORE_BASE64` | Yes | Contents of `upload-keystore.jks.base64`. One line is fine. |
| `ANDROID_KEYSTORE_PASSWORD` | Yes | Keystore password. |
| `ANDROID_KEY_PASSWORD` | Yes | Key password. |
| `ANDROID_KEY_ALIAS` | No | `upload`. Gradle uses `upload` when this is empty. |
| `PLAY_SERVICE_ACCOUNT_JSON` | Only if the workflow upload toggle is on | Service account JSON key. See below. |
| `GOOGLE_SERVICES_JSON` | Only for FCM | Entire `google-services.json`. See Firebase below. |

Do not put these values in the repo, in a pull request, or in a chat.

## 3. What the workflow does

`.github/workflows/android-release.yml` is `workflow_dispatch` only. Inputs:

- `track`: `internal` or `alpha`
- `upload`: off by default. On sends the AAB to that Play track.

Actions → Android release → Run workflow. The job:

1. `npm ci` in `frontend/` and `npx cap sync android`. The shell loads `https://enchantedspoon.app`. The Next.js production build is not part of the AAB. `frontend/mobile/www` is only the fallback `webDir`.
2. Writes `google-services.json` when `GOOGLE_SERVICES_JSON` is set.
3. Decodes `ANDROID_KEYSTORE_BASE64` into a temp keystore.
4. Runs `./gradlew bundleRelease`. The artifact is `frontend/android/app/build/outputs/bundle/release/app-release.aab`.
5. Uploads that AAB as a GitHub Actions artifact (kept 14 days).
6. If `upload` is on, publishes it with [r0adkll/upload-google-play](https://github.com/r0adkll/upload-google-play) `v1.1.5` and `PLAY_SERVICE_ACCOUNT_JSON`. `status` is `completed`, so testers can install it. The action input is `tracks`. `internal` is Play internal testing. `alpha` is the Play Developer API name of the default closed testing track. If the console shows a different closed-track id, say so before turning the toggle on.

`versionCode` in CI is `GITHUB_RUN_NUMBER` for this workflow. Do not also set `ANDROID_VERSION_CODE` on the workflow, or every run will reuse one code and Play will reject it.

The manual Play upload should be an artifact from this workflow, not a separately numbered local build. Run the workflow once with `upload` off, download the AAB, and upload that file. The next run uses the next run number. A local `bundleRelease` is for checking the build. Upload it only if its `ANDROID_VERSION_CODE` has never been used and is higher than every code already on Play, and then skip any CI run that would reuse a lower number.

## 4. First upload and Play App Signing

The Publishing API returns an error until the app exists in the Play Console. The first AAB is uploaded by hand.

1. Play Console, create the app with application id `com.enchantedspoon.app` if it is not there yet. This uses the owner's existing developer account.
2. Run the workflow with `track` = `internal` and `upload` off.
3. Download the AAB artifact.
4. Play Console → Test and release → Internal testing → Create release → upload that AAB.
5. Enroll in Play App Signing when the console asks. The keystore from the script is the **upload key**. Google generates and holds the **app signing key**. Confirm the upload certificate SHA-1 / SHA-256 matches what the script printed.
6. After enrollment, Play Console → Test and release → App integrity (or Setup → App signing) shows the app signing certificate. Keep those fingerprints. Firebase asks for a signing certificate SHA-1 when the Android app is registered; use the app signing certificate from this page, and add the upload certificate as well if Firebase lists both.

The service account cannot create the app. Create it with this manual upload first. Then:

1. Play Console → Setup → API access. Link the Cloud project Play offers.
2. Create a service account and download its JSON key once.
3. Grant that account permission to release to testing tracks for this app.
4. Store the JSON in `PLAY_SERVICE_ACCOUNT_JSON`.
5. Later workflow runs can set `upload` on.

## 5. Internal track, then closed track

Internal testing is the smoke test. It can be an email list, and builds show up quickly. It does **not** count toward Google's production-access requirement.

Closed testing does. In the Play Developer API the default closed track is `alpha`. In the console it is Closed testing.

1. Create a Google Group for testers (for example `enchanted-spoon-closed-testers@googlegroups.com`).
2. Add at least 12 people who will stay opted in. They must use the Google account they will use on the device.
3. Play Console → Closed testing → manage the track → testers → paste the group email.
4. Copy the opt-in link. Each tester joins the group, opens the link, opts in, and installs from Play.
5. Ship the closed-track build with the workflow: `track` = `alpha`, `upload` on, after the manual first upload and the service account exist. Until the API is ready, upload the workflow artifact to the closed track by hand the same way as internal.

### 12 testers for 14 days

For a personal Play developer account, production access requires a closed test with **at least 12 testers opted in for 14 consecutive days**. Invited-but-not-opted-in does not count. Internal testing does not count. Check the production-access page in Play Console for the live counter, and keep all 12 opted in for the whole window.

Calendar for this release (2026):

| Date | What |
| --- | --- |
| Nov 2–3 | Internal testing. Install the signed AAB, sign in, open the paywall. |
| Nov 4 | Closed testing starts. This is day 1 if all 12 testers opt in that day. |
| Nov 17 | Day 14, if day 1 was Nov 4. |
| Nov 18 | Day 15. Apply for production access if the counter says the requirement is met. |
| Nov 24 | Latest day 15 in this plan. That is the application date if the closed test cannot start until Nov 10. Do not start the closed test later than Nov 10 if Nov 24 is the latest application date. |

Apply on day 15. Do not promote to production from this workflow. There is no production track input.

## 6. License testers (sandbox purchases)

License testing and the closed-test list are different.

- The Google Group (or the internal email list) controls who can **install** the build.
- License testers can make **sandbox subscription purchases** without being charged.

Play Console → Settings → License testing. Add the Gmail addresses that should buy in the sandbox, and leave the license response as licensed. Those people still need to be on the testing track to install the app. A license tester is not a substitute for one of the 12 closed-test opt-ins.

Run a sandbox purchase only after the subscription products exist and RevenueCat is pointed at them. `docs/MOBILE.md` has the server flags (`NATIVE_IAP_ENABLED`, `REVENUECAT_*`). Leave purchases off until those are set and the web app is redeployed.

## 7. Firebase `google-services.json` (FCM)

Push needs a Firebase Android app with package `com.enchantedspoon.app`. Download `google-services.json` and keep it out of the repo.

- Local release builds: place it at `frontend/android/app/google-services.json`. That path is gitignored. `frontend/android/app/build.gradle` applies the Google services plugin when the file is present and non-empty.
- CI: paste the whole file into secret `GOOGLE_SERVICES_JSON`. The workflow writes it before `bundleRelease`. If the secret is missing, the bundle still builds and FCM is omitted.

`FCM_SERVER_KEY` stays on the API service, as in `docs/MOBILE.md`. The JSON file in the app and the server key are both required before trial nudges can be delivered.

## 8. Create the subscriptions after the first upload

Play does not offer subscription products until the app exists and an AAB has been uploaded. Do this after section 4, in the owner's Play Console session:

1. Monetize with Play → Products → Subscriptions.
2. Create `com.enchantedspoon.app.pro.monthly` at $6.99 (US) with a base plan and a 7-day free trial.
3. Create `com.enchantedspoon.app.pro.annual` at $49.99 (US) with a base plan and a 7-day free trial.
4. Activate both.
5. In RevenueCat, attach the Android app and those product ids to entitlement `pro`.

The same ids are in `docs/MOBILE.md`. The billing permission Play looks for is `com.android.vending.BILLING`. It is merged from `com.android.billingclient:billing`, which `@revenuecat/purchases-capacitor` pulls in through `purchases-hybrid-common` and `com.revenuecat.purchases:purchases`. Do not remove that plugin. The app manifest does not declare the permission itself.

## 9. Local release build

```bash
cd frontend
npm ci
CAPACITOR_SERVER_URL=https://enchantedspoon.app npx cap sync android
cd android
./gradlew bundleRelease
```

The AAB is `frontend/android/app/build/outputs/bundle/release/app-release.aab`. `bundleRelease` fails if signing is not configured. Debug builds do not need the upload key.
