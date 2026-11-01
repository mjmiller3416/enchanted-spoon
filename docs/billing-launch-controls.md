# Billing launch controls (implementation review)

This document describes code behavior, not the state of any live account. No live
credential, webhook creation, provider configuration or deployment is authorized by it.

## Activation and version contract

- `STRIPE_CHECKOUT_ENABLED` defaults to false. Checkout returns HTTP 503 before customer
  creation unless explicitly enabled. Portal and webhook processing are independent so
  existing customers can still manage billing while new sales are closed.
- `stripe==16.0.0` is pinned. API calls and synthetic snapshot fixtures use
  `2026-09-30.endive`. Webhook signature verification additionally requires that version
  and mode agreement with the configured key; production accepts live events only.
- The signed route remains `/api/webhooks/stripe`. Configure snapshot events, not thin
  notifications. Match endpoint version before switching: older snapshots are rejected.
- Required runtime variables: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`,
  `STRIPE_PRICE_ID_PRO`, HTTPS `FRONTEND_URL`, and the explicit checkout activation flag.
  Secrets belong in approved server-side secret storage, never public/client variables.
- Portal sessions use the default Stripe configuration; no portal configuration ID is
  currently read from application settings.

## Event behavior

Checkout completed and asynchronous succeeded/failed, invoice paid/payment failed, and
subscription created/updated/deleted are wake-ups to reconcile CURRENT Stripe state.
Neither event delivery order nor a checkout redirect grants access. A customer must
already match the app's stored Stripe customer mapping; client_reference_id cannot bind
an unrelated user. One-off/unknown-mode checkout events cannot grant subscription access.

Under a per-user database row lock, reconciliation lists that customer's subscriptions
and filters to the configured Pro Price. Active subscriptions require a paid latest
invoice before granting access; authoritative trialing status retains the existing trial
semantics. Existing Pro users keep access during past_due; first-payment failure does
not grant new access. A current paid replacement subscription wins over an older canceled
one. Access is removed only when all matching subscriptions have terminal Stripe states
(canceled, unpaid or incomplete_expired). Unknown/unsettled states and unmatched Prices
leave access unchanged and require review. Provider errors or truncated lists return a
retryable error without committing either access changes or the event receipt.

Refunds, disputes and early fraud warnings are review-only: no refunds, cancellation,
subscription mutation or entitlement penalty is performed. Only event ID, event type,
review/outcome code and receipt timestamp are stored. No raw payload, payment details,
customer email or exception text is saved to the ledger or emitted by this handler.

## Database and permissions implications

Migration `a6c1e4f9d3b5` follows `f5b0d3e8c2a4` and adds `billing_events`. Receipt and
entitlement changes commit atomically; the event-ID primary key deduplicates deliveries.
Existing user rows and allowances are not migrated by this new table. Apply migrations
before serving this release. PostgreSQL row locks serialize customer reconciliation;
SQLite tests cover committed-state behavior but do not certify PostgreSQL concurrency.

Runtime calls require Customers Write, Checkout Sessions Write, portal sessions Write,
and now Subscriptions Read for reconciliation. Expanded latest invoices may require
Invoices Read under the chosen restricted-key policy; verify exact minimum permissions
in an approved sandbox before granting the corresponding live scope. Webhook management,
refunds, payouts and product/Price creation are not runtime operations. No permissions
were created or expanded as part of implementing these controls.

The review ledger has no automatic notification destination or administrative UI yet.
A real operator review process and retention policy are release gates. Event IDs are
pseudonymous references to Stripe records, not anonymous data. The migration downgrade
drops receipts, so it is not a routine production rollback: retaining the table while
rolling application code back preserves duplicate/review evidence. Raw-event export or
copying production records into test environments is not part of this implementation.

## Controlled setup sequence and decisions

1. Keep checkout disabled; validate pinned-version lifecycle/permissions in an isolated
   nonproduction target using synthetic customers and test mode.
2. Approve persistent credentials and webhook creation separately. There is no assumed
   disabled-at-create webhook option. Coordinate endpoint creation/signing-secret setup
   with the receiving backend configuration and version; allow for retries during setup.
3. Review and approve migration/deployment with matching-mode key, Price and signing
   secret. This app accepts one signing secret, so keep test billing on a separate target.
4. Verify live delivery without making an unapproved payment; confirm portal behavior,
   owner terms and the private review queue process. Then authorize enabling checkout.

Owner decisions still required: refunds/dispute/fraud response process, review ownership
and alert destination, review-record retention, and policy for grace beyond Stripe's
past_due state. No automatic business-policy action is inferred from those signals.
The exact newly created provider resources and private operating findings stay outside
this public-safe implementation document.
