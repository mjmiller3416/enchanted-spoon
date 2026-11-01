# Soft-launch readiness checklist

This branch prepares a web soft launch. Publication and deployment require a separate
review checkpoint. Native iOS/Android releases are outside this implementation.

## Implemented behavior

- Optional images reserve a shared image allowance atomically before provider calls.
  Quota exhaustion preserves recipe success; partial photo success consumes one action,
  and total failure releases the reservation. Images are opt-in by default.
- New-account allowances are Free 1/10/10/5 and Pro 10/50/50/100 for photo actions,
  shared AI requests, assistant messages and imports. Proposed Pro price: US$4.99/month
  (499 cents). These are feature allowances, not guaranteed provider dollar budgets.
- The usage-plan migration preserves existing accounts' legacy allowances. Enforcement
  and displayed limits resolve the same cohort. Ordinary recipes, Menu, shopping and
  cooking remain separate from optional AI use.
- Feedback verifies a private destination before sending and reports delivery failure
  honestly. Metadata excludes URL credentials, query strings and fragments.
- Production billing requires live configuration and HTTPS return URLs. Webhook mode
  checks use the actual Stripe SDK Event interface after signature verification.
- Marketing describes supported imports, estimated nutrition and shopping categories.
  Privacy and subscription disclosures remain subject to owner review.
- Frontend CI includes regression tests; production builds use webpack.

## Validation

- Backend: 556 tests passed, including real signed synthetic Stripe events, migration
  cohort preservation, account isolation/deletion and core recipe/Menu/shopping flows.
- Frontend: 31 tests passed; lint, typecheck and production build passed.
- AI/billing checks used mocks or synthetic payloads; no paid provider requests were
  required. Public pricing/privacy pages received local responsive browser checks.
- Signed-in identity-provider workflows and native device/store certification are
  separate release checks. Test results do not establish production configuration.

## Release review checklist

- Approve operator identity, support contacts, subscription/refund terms and privacy copy.
- Verify intended live Price, webhook delivery, cancellation and subscription lifecycle.
- Verify support delivery, monitoring, backup retention and an isolated restore rehearsal.
- Exercise registration, reset, deletion and save-to-Menu-to-shopping-to-cook journeys
  using an approved disposable identity and nonbillable test services.
- Review migration compatibility and existing-account entitlements before deployment.
- Review staging results and obtain the production deployment checkpoint.

Keep private operational findings outside the repository. See the owner-review legal
wording in soft-launch-legal-draft.md; placeholders must be resolved before publication.
