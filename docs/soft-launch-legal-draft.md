# Owner-review draft: privacy and subscription disclosures

NOT APPROVED FOR PUBLICATION. This is a factual drafting aid, not legal approval.
Retain Enchanted Spoon temporarily; do not invent an operator or refund commitment.

## Decisions required before publication

- [OWNER: legal operator name, jurisdiction and required business/contact address]
- [OWNER: verify info@enchantedspoon.app receives support and privacy requests]
- [OWNER: refund policy, cancellation effective date and handling of billing disputes]
- [OWNER: service territory/age rules and applicable consumer disclosures]
- [OWNER: retention periods for app records, logs, backups and each provider]
- [OWNER: rights-request process, response responsibilities and final legal review]

## Factual privacy wording for review

Enchanted Spoon is operated by [LEGAL OPERATOR]. Clerk handles account sign-in.
The app stores account information, recipes, ingredients, Menu entries, shopping
lists, cooking history, preferences and AI usage counts to provide its features.
Google Gemini processes the prompts and recipe context supplied to AI features.
Cloudinary hosts recipe images. Railway hosts the app and database. Stripe handles
subscription payments. Sentry receives technical error reports. A configured GitHub
support tracker may receive feedback only after its private visibility is verified.
If private delivery is unavailable, the form reports failure and offers support email.
Contact support to request review or removal of previously submitted feedback.

Browser storage includes preferences and assistant history. Authentication providers
use cookies. Do not claim no tracking cookies or no personal information in error
reports without reviewing actual provider settings and event samples.

Settings provides supported data exports and account deletion. These exports are not
complete exports of all provider records. Deletion first attempts billing cancellation,
then removes app content and the account, requests owned image removal and attempts
Clerk identity deletion. External failures, provider retention, past feedback, logs
and backups may leave records. State approved retention and support procedures here:
[OWNER RETENTION AND FOLLOW-UP PROCESS]. Do not promise immediate complete erasure.

## Subscription wording for review

The proposed new-account Pro plan costs US$4.99 per month. Before activating live
checkout, confirm the live Price, taxes, renewal timing, portal and refund policy.
If configured as intended: the subscription renews monthly until canceled; users can
manage cancellation through Settings billing. [OWNER: confirm exact cancellation
and refund terms against the configured live Stripe portal before publishing.]

New-account monthly AI allowances: Free 1 photo action, 10 shared AI requests,
10 Genie messages and 5 imports; Pro 10, 50, 50 and 100 respectively. Photo actions
may produce up to a square/banner pair; single-image regeneration also consumes an
action. Shared AI requests cover generation, nutrition estimates, meal ideas and tips.
Allowances reset by calendar month and do not roll over. Existing accounts retain
their legacy allowances, shown in their usage view. Ordinary saved recipes, Menu,
shopping and cooking are distinct from optional AI use. Do not call AI unlimited.

AI results, including nutrition, are estimates and can be inaccurate. Users should
check ingredients, cooking instructions and suitability. Avoid unsupported claims
about medical suitability, allergen safety or guaranteed nutritional accuracy.

## Evidence and publication gate

Sources: app/services/account_service.py, core/usage_limits.py, persisted usage_plan
migration, services/github_service.py, core/observability.py, marketing privacy/terms
pages and the release checklist in soft-launch-readiness.md (backend paths relative
to backend/). Verify live billing configuration before publication.
Do not describe paid subscriptions as live solely because test checkout exists.
This draft does not establish contractual commitments. Owner decisions and review
must be incorporated into the actual pages before public launch approval.
