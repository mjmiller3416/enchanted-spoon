# Phase 0 Findings & Go/No-Go — AI Provider Evaluation

**Decision run:** 2026-08-11 · production baseline `gemini-3.5-flash` (thinking
disabled) vs `gpt-5.6-terra` vs `claude-sonnet-5` · all 5 services · **0 API errors**.
Numbers: [`scorecard.md`](scorecard.md). An earlier exploratory run used
`gemini-3.6-flash`; archived at [`scorecard-gemini-3.6.md`](scorecard-gemini-3.6.md).

## TL;DR — NO-GO on switching. Stay on Gemini 3.5-flash.

Against the **real production config**, `gemini-3.5-flash` is the **fastest and
cheapest provider on every service**, with quality competitive-to-best. Neither
GPT-5.6 Terra nor Claude Sonnet 5 beats it on quality-adjusted cost anywhere. The
money-saving Phase 0 outcome holds: **don't build the gateway to migrate; keep
Gemini 3.5**. Keep GPT-5.6 Terra on the shelf as a validated fallback / second
source (Phase 5), and as the clean upgrade for the two structured services *if*
Gemini's occasional malformed JSON proves user-impacting (see below).

> **Why the re-baseline mattered (read this).** The first run measured
> `gemini-3.6-flash` and made switching look attractive — 3.6 was the *slowest and
> most token-heavy* provider because it **cannot disable thinking** (49k of its 76k
> tokens were thinking) and it truncated structured JSON. Swapping to production's
> `gemini-3.5-flash` (thinking disabled) **flipped the result**: Gemini went from
> worst to best on cost/latency. Lesson: measure the config you actually ship.
> Corollary: **do not adopt `gemini-3.6-flash`** for these single-shot tasks — its
> forced thinking is a strict downgrade.

## The numbers (production baseline — from scorecard.md)

| Axis (5 services) | gemini-3.5-flash | gpt-5.6-terra | claude-sonnet-5 |
|---|---|---|---|
| Total cost | **$0.13** | $0.20 | $0.31 |
| Total tokens | **26,870** | 25,048 | 37,634 |
| Latency p50 — tips | **0.96s** | 1.72s | 2.91s |
| Latency p50 — meal | **0.98s** | 1.52s | 3.02s |
| Latency p50 — nutrition | **1.18s** | 1.65s | 3.10s |
| Latency p50 — import | **2.23s** | 3.36s | 5.82s |
| Latency p50 — recipe-gen | **4.56s** | 8.70s | 11.18s |

Gemini 3.5 is **fastest and cheapest on all five**. Quality (all near-tie):

| Service (metric) | gemini-3.5 | gpt-5.6 | claude-5 |
|---|---|---|---|
| Cooking tips (judge) | 91% | **93%** | 85% |
| Meal suggestions (judge) | **84%** | 81% | 78% |
| Recipe import (fidelity+routing) | **100%** | **100%** | **100%** |
| Recipe generation (schema) | 88%¹ | 96% | **100%** |
| Nutrition estimation (schema+band) | 83%¹ | **100%** | **100%** |

¹ **Gemini's one weakness:** occasional malformed/truncated JSON on the two
heaviest structured services — recipe-gen **13%** (1/8), nutrition **17%** (1/6).
Import was clean (100%). GPT-5.6 and Claude were 0% malformed everywhere. This is a
known production trait — the services already wrap Gemini with `_extract_json`
tolerance + retry/fallback, so effective user-facing reliability is higher than the
raw rate. Sample sizes are small (n=6–8), so treat 13–17% as "occasionally," ±1 sample.

## Go / No-Go — per service

| Service | Job (weight) | Winner | Decision |
|---|---|---|---|
| **Cooking tips** | latency/cost | **Gemini 3.5** (fastest, cheapest, quality tie) | **STAY** — nothing beats it here |
| **Meal suggestions** | latency/cost | **Gemini 3.5** (fastest, cheapest, top judge score) | **STAY** |
| **Recipe import** | quality | tie (all 100%); Gemini fastest+cheapest | **STAY** |
| **Recipe generation** | quality | Gemini fastest/cheapest but 13% malformed; GPT/Claude cleaner | **STAY & MONITOR** — if malformed rate is user-impacting, GPT-5.6 is the drop-in |
| **Nutrition estimation** | quality | Gemini fastest/cheapest but 17% malformed; GPT/Claude 100% | **STAY & MONITOR** — same; GPT-5.6 is the clean upgrade candidate |

**Net: "no" to switching, everywhere** — the plan's money-saving successful outcome.
Phases 1–4 (the gateway build + migration) are **not** justified by this data. The
one open thread is Gemini's structured-JSON reliability on recipe-gen/nutrition;
resolve it by (a) widening those golden sets to get a tighter malformed-rate
estimate, and (b) checking prod telemetry for actual parse-failure/retry rates. If
it's real, scope a *targeted* switch of just those two services to GPT-5.6 Terra
(cheapest 0%-malformed option) — that, and only that, would define a minimal Phase 1.

## What to keep from Phase 0 regardless

- **GPT-5.6 Terra as the Phase 5 fallback provider** — it matched Gemini on quality,
  is 0% malformed, and is cheaper than Claude. Best secondary source if Gemini has an
  outage or a specific service needs rock-solid JSON.
- **This harness, re-runnable.** When a new model drops, `npm run all && npm run
  scorecard` re-answers "does it beat our routing?" in minutes.

## Caveats (see README for detail)

- **Temperature asymmetry:** Gemini keeps per-service temperature; GPT-5.6 and
  Sonnet 5 reject `temperature` and run at default (slightly narrows their
  open-ended variety). With the 3.5 baseline all three run non-thinking, so the
  thinking asymmetry from the 3.6 run no longer applies.
- **Judge self-preference:** open-ended scores use a Claude judge
  (`claude-sonnet-4-6`); the ~few-point tip/meal gaps are within noise. Cross-check
  with a non-Claude judge before over-reading them (protocol in README).
- **Small n:** 5–8 rows per structured service. Widen the golden sets before making
  a switch call on the malformed-JSON rates.
