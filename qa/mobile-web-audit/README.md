# Mobile web audit

Browser emulation of https://enchantedspoon.app (override with `AUDIT_BASE_URL`). This is Chromium, WebKit, and Firefox on a desktop VM. It is not a Samsung phone, not Android 17, and not iOS.

Playwright 1.56.1 device names are used unchanged when a preset exists. Galaxy S26 Ultra, Pixel 9 Pro XL, and Galaxy Tab S10 FE are **not** in that library. Those contexts are labeled approximations (CSS viewport, DPR, touch, constructed user agent). Sources and disagreements are in `audit.mjs`.

The script does not sign in, submit email addresses, start Google OAuth, open Stripe Checkout, or call recipe-import or other paid generation endpoints.

```bash
cd qa/mobile-web-audit
npm install
npx playwright install chromium webkit firefox
# Linux host libraries, if the browser fails to launch:
# sudo npx playwright install-deps
AUDIT_OUT=/tmp/enchanted-spoon-mobile-audit npm run audit
```

`AUDIT_OUT` receives `results.json`, `summary.md`, and screenshots. Authenticated app screens are expected to redirect to `/sign-in` in this environment.
