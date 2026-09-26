# MealGenie — Feedback & Error Reporting Architecture

Reference notes, August 2026. Not a build prompt — this is the reasoning to work from
while making changes.

> **Status (2026-08-03):** Recommendation 1 shipped in simplified form — `POST /api/feedback`
> creates a GitHub issue directly (`app/api/feedback.py`, `app/services/github_service.py`).
> No admin panel, no stored `feedback_reports` table (not even the join table proposed below —
> there's currently no server-side record of who filed what). Recommendation 2 (Sentry/GlitchTip)
> is **not started** — this is still the largest open gap from the "Now (pre-launch)" list.
>
> **Update (2026-09-26):** Recommendation 2 is **built, pending account setup** — backend
> (`app/core/observability.py`) and frontend (`@sentry/nextjs`, `src/lib/sentry.ts`) report to
> Sentry once `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` are set; events carry the Railway commit
> SHA as the release and only the internal user id. Issues now cite `user #<id>` with a link to
> the admin Users list, which can search by id — a lighter substitute for the join table below
> (no "what else did this user file" yet).

---

## The core principle

**Store the work where the work happens. Only add a database row when you need a
relationship GitHub genuinely cannot express.**

The admin panel felt cumbersome not because the schema was wrong, but because a feedback
admin panel is a build-your-own issue tracker. It meant owning triage UI, filtering,
status transitions, search, and notification — all of which GitHub already provides, and
none of which is the interesting part of the product. State was duplicated into a place
that was worse at holding it, and then two places had to be checked.

Copies drift. Any field in your database that is also a field in GitHub will eventually
disagree with GitHub, and GitHub will be the one that's right.

---

## The decomposition

What got mashed together in the admin panel is really three separate systems with
different shapes:

| | What it is | Volume | Needs |
|---|---|---|---|
| **1. Solicited feedback** | Someone deliberately tells you something | Low, high signal | A reply path back to a human |
| **2. Unsolicited errors** | Something broke and nobody told you | High | Grouping, dedup, counts, stack traces |
| **3. Resolution** | What you're doing about it | — | GitHub Issues (already works) |

The three criteria that matter to you — user association, notification in VSCode,
`@claude` tagging — all belong to **1** and **3**.

**System 2 does not exist yet, and it is the largest gap.** User-reported bugs are the
tip of the iceberg. Most people who hit a bug don't file a report; they stop using the
app. At a public release, the errors nobody tells you about will outnumber the ones they
do by a wide margin.

---

## Recommendation 1 — A join table, not a records table

```
feedback_reports
  id
  user_id                FK
  github_issue_number
  github_issue_url
  page_url
  created_at
```

That's the whole thing. Deliberately absent:

- **`status`** — GitHub owns open/closed
- **`admin_notes`** — that's what issue comments are
- **`category`** — that's the label
- **the message body itself** — it's in the issue

This table answers the three questions GitHub can't:

1. **Who filed this** — privately, without putting identity in the issue
2. **What else has this user filed** — pattern across reports from one person
3. **How do I reach them when it closes** — join back to the user record

No admin UI required. It's a lookup, not a workspace. If you ever want a view, it's one
read-only page listing reports with a link out to GitHub — not a place where work happens.

---

## Recommendation 2 — Sentry (or GlitchTip)

This is the highest-value change on the list.

**GlitchTip** is a self-hostable, Sentry-SDK-compatible alternative that runs fine on
Railway if you'd rather not add a vendor. Same client code either way, so the decision is
reversible.

What it gives you that a feedback form structurally cannot:

- **Stack traces** — the actual failing line, not a user's description of the symptom
- **Breadcrumbs** — what the user clicked in the 30 seconds before the crash
- **Grouping** — 400 occurrences of one error are one entry with a count of 400, not 400
  separate reports
- **Release tagging** — which build the error came from
- **Errors from users who never file anything**

It has a GitHub integration that creates an issue from an error, which preserves both
things you like about the current setup: it pops up in VSCode, and you can `@claude` it.

### Why this matters specifically for the Claude workflow

`@claude` on *"the photo is wrong"* is a research assignment — Claude has to reproduce,
guess at context, and explore.

`@claude` on a Sentry issue with a stack trace, the release SHA, and the click path is a
**fix**.

The quality of Claude's output on these issues is almost entirely a function of the
quality of the report. That's an argument for capturing context automatically rather than
asking users to describe it — which is also the answer to "users write bad bug reports."
Don't make the form longer. Capture more and ask less.

---

## Things easy to overlook

### PII in a public repo
If the repo is public, user emails in issue bodies are a leak, and user-written free text
can contain anything — addresses, other people's names, whatever they paste in. Put an
opaque user ID in the issue and resolve it through the join table. Lower stakes on a
private repo, but the habit is worth forming before launch rather than after.

### There is no reply path
Users cannot respond to a GitHub issue. With Maryann this is irrelevant — you talk at
dinner. With strangers, "what browser were you on?" becomes impossible, and "we fixed
this" never gets delivered. A support email address you actually watch is genuinely
enough at first; the point is that *some* channel exists.

### A public endpoint that creates GitHub issues is an abuse vector
Rate limit per user. Treat the `issues:write` PAT as a real credential — scoped to the
one repo, rotated if it ever touches a log.

### Release tagging
Without knowing which build a report came from, you can't tell whether it's already
fixed. Stamp the commit SHA into every feedback submission and every error event. This is
cheap now and impossible to backfill later.

### You can't count
GitHub Issues has no dedup. "50 users hit this" and "1 user hit this" look identical.
Fine at current scale — and it's the specific reason people eventually adopt a real
feedback tool. Sentry solves this for errors; solicited feedback stays uncounted until
volume makes it hurt.

### Free text underperforms
"It doesn't work" is the modal bug report, and no amount of form design fixes that. See
above: capture more automatically, ask less.

---

## Sequencing

### Now (pre-launch)
- [ ] Add Sentry or GlitchTip to frontend and backend
- [ ] Wire its GitHub integration so errors can become issues
- [ ] Add the `feedback_reports` join table
- [ ] Stamp commit SHA into feedback submissions and error events
- [ ] Leave everything else exactly as it is

That's roughly a weekend, and it closes the single largest gap.

### At public beta
- [ ] Reply channel — a support email you actually watch
- [ ] Rate limit the feedback endpoint per user
- [ ] Move issues to a private repo if the code repo is public
- [ ] Swap user email for opaque ID in issue bodies

### Later, only if triage starts hurting again
Voting, dedup for solicited feedback, public roadmap, dedicated feedback tooling. This is
a problem you'd be lucky to have. You'll know you're there because the pain will be
specific and nameable, not vague.

---