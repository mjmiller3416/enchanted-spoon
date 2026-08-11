# Whiskful AI provider evaluation (Phase 0)

The **ruler before the cut**. This is the offline eval harness from
[`docs/plans/ai-gateway-and-eval.md`](../../docs/plans/ai-gateway-and-eval.md)
Phase 0. It answers one question — **"is switching any AI service off Gemini
worth it?"** — with numbers, **before** any gateway refactor touches app code.

It runs each service's real production prompt through Gemini, OpenAI, and Claude
side-by-side and scores them. It does **not** import or depend on `app/` — it
calls each provider directly via [promptfoo](https://promptfoo.dev), so it can
run and produce a verdict even if the answer is "no, keep Gemini everywhere"
(a *successful* Phase 0 outcome).

## Layout

```
evals/
├── configs/       one promptfoo config per service (providers + prompt + tests + asserts)
├── prompts/       the REAL service prompts, extracted verbatim (see "Faithfulness")
├── datasets/      golden inputs per service (+ ground truth for structured services)
├── assertions/    programmatic checks for the structured tier (JS, bias-free)
├── scorecard/     scorecard.md (the artifact) + generate.mjs (fills it from results)
├── output/        raw per-service results JSON (gitignored)
└── package.json   pinned promptfoo + run scripts
```

## Quick start

```bash
cd backend/evals
npm install                       # installs promptfoo 0.122.0 locally

# Keys: the three dedicated eval keys live in backend/.env as GEMINI_EVAL_API_KEY /
# OPENAI_EVAL_API_KEY / ANTHROPIC_EVAL_API_KEY (each $5-capped). promptfoo reads the
# STANDARD names, so map them for the run (from backend/evals/, sh/bash):
export GOOGLE_API_KEY=$(grep '^GEMINI_EVAL_API_KEY=' ../.env | cut -d= -f2- | tr -d '\r')
export OPENAI_API_KEY=$(grep '^OPENAI_EVAL_API_KEY=' ../.env | cut -d= -f2- | tr -d '\r')
export ANTHROPIC_API_KEY=$(grep '^ANTHROPIC_EVAL_API_KEY=' ../.env | cut -d= -f2- | tr -d '\r')

npm run validate                   # structural check, NO API calls / NO spend
npm run all                        # runs all 5 services (this spends money)
npm run scorecard                  # writes scorecard/scorecard.md from output/*.json
npm run view                       # optional: promptfoo's side-by-side web UI
```

Run one service at a time with `npm run tips` / `recipe-gen` / `import` /
`nutrition` / `meal`.

> **Cost:** a full `npm run all` is on the order of ~150 generations (5 services ×
> ~3–8 inputs × 3 providers) plus the LLM-judge calls for the two open-ended
> services. On the cost-tier models below that is cents, not dollars — but it is
> **not** zero, and it hits three billing accounts. `npm run validate` is free.

## Which models

The committed matrix (the **production baseline**):

| Provider | Model id | Mode in this eval |
|---|---|---|
| Google | `google:gemini-3.5-flash` | thinking **disabled** (`thinkingBudget: 0`) — matches production |
| OpenAI | `openai:gpt-5.6-terra` | `reasoning_effort: none` (fast, non-thinking) |
| Anthropic | `anthropic:messages:claude-sonnet-5` | `thinking: {type: disabled}` |

Change models by editing the `providers:` ids in `configs/*.yaml`.

> **`gemini-3.6-flash` was also evaluated** (the initial run). It behaves very
> differently and its results are archived in
> [`scorecard/scorecard-gemini-3.6.md`](scorecard/scorecard-gemini-3.6.md) with the
> comparison in [`scorecard/findings.md`](scorecard/findings.md). To re-test 3.6, swap
> the Gemini id to `google:gemini-3.6-flash`, set `thinkingConfig: {includeThoughts: false}`
> (it **cannot** disable thinking — `thinkingBudget: 0` → 400), and raise the tips/meal
> `maxOutputTokens` to 2048 (its thinking otherwise truncates the answer).

### ⚠️ Per-model parameter reality (probed against each API, 2026-08-11)

These are newer-generation models with real constraints that the configs already encode:

- **Gemini 3.5-flash** disables thinking with `thinkingConfig: {thinkingBudget: 0}`
  (production's setting) and keeps its per-service `temperature`. Fast, lean, single-shot.
- **GPT-5.6 Terra** rejects `temperature` (only default 1) and `max_tokens`
  (must use `max_completion_tokens`). Run at `reasoning_effort: none` so it behaves
  as a fast single-shot model (0 reasoning tokens confirmed).
- **Claude Sonnet 5** rejects `temperature`; run with `thinking: {type: disabled}`.

### ⚠️ One asymmetry to keep in mind when reading the scorecard

**Temperature.** Gemini keeps its tuned per-service temperature (e.g. 0.9 for tip
variety); GPT-5.6 and Claude Sonnet 5 reject `temperature` and run at their default.
This slightly narrows GPT/Claude output variety on the open-ended services — inherent
to those models, not a harness choice. (With the 3.5 baseline all three now run
**non-thinking**, so the thinking asymmetry that applied to the 3.6 run is gone.)

## The judge & self-preference bias (read this)

Open-ended services (tips, meal suggestions) can't be diffed, so they're scored
by an **LLM-as-judge**: an absolute `llm-rubric` score per candidate on identical
criteria (head-to-head ranking is read from those scores). Two things to keep honest:

1. **There is no fully-neutral judge** — all three candidate families also appear
   as competitors. The default judge is `anthropic:messages:claude-sonnet-4-6`
   (strong at structured judging, and temperature-tolerant so it runs cleanly).
   That means the **Claude column's open-ended scores carry a self-preference
   caveat.**
2. **Protocol: cross-check with a second-family judge.** The Claude candidate is
   `claude-sonnet-5` and the judge is `claude-sonnet-4-6` (same family) — so the
   Claude column's open-ended scores especially need a cross-check. Re-run the two
   open-ended configs with the judge changed to `openai:gpt-5.6-terra` (or
   `google:gemini-3.5-flash`) — edit `defaultTest.options.provider` in
   `configs/cooking-tips.yaml` and `configs/meal-suggestions.yaml`. If a
   Claude-vs-X result flips between judges, treat it as inconclusive.

The **structured tier is bias-free** — it's graded by deterministic JS
assertions (JSON parses, matches the DTO schema, enums valid, quantities sane,
macros reconcile via the 4/4/9 rule, import keeps every ingredient). Those are
your strongest, cheapest signal; the judge scores are directional.

## Faithfulness (measure the providers, not a rewrite)

- **Prompts are the production prompts, verbatim.** `prompts/*` are transcribed
  from the service modules (`cooking_tips.py`, `recipe_generation/config.py`,
  etc.), converting only Python `.format` doubled braces `{{ }}` → single `{ }`
  and keeping `{var}` → `{{var}}` for promptfoo templating.
- **Per-service params mirror production** — each config sets that service's
  exact `temperature` / `max_tokens` and, for the JSON services, JSON mode. It
  also disables Gemini thinking (`thinkingConfig.thinkingBudget: 0`) to match the
  app. If your promptfoo version rejects that key, remove it and note in the
  scorecard that Gemini ran with default thinking (slightly higher quality/cost).
- **JSON tolerance matches the app.** OpenAI/Gemini use native JSON mode; Claude
  has none, so `assertions/lib.js` strips markdown fences and decodes the first
  object exactly like the services' parse path — and the malformed-JSON rate is
  itself a reported metric.
- **Per-service API keys.** Production uses a separate Gemini key per service for
  billing attribution (landmine #3). The offline eval deliberately collapses to
  one key per provider — it measures the *model*, not per-feature billing.
  Preserving per-(provider, service) keys is a Phase 1 concern.

## Tiers & metrics

| Tier | Services | How graded |
|---|---|---|
| **Structured** | recipe generation, recipe import, nutrition estimation | deterministic JS assertions (per-metric pass rates) |
| **Open-ended** | cooking tips, meal suggestions | LLM-judge rubric |
| **Conversational** | Genie chat (`configs/genie-chat.yaml`) | voice/personality rubric + **human side-by-side read** — see below |

Every run also records **latency p50/p95**, **cost/call**, and **error rate** per
provider (promptfoo computes these). Consistency/variance needs `--repeat N`.

## Genie chat eval (the conversational feature)

Separate from the 5 single-shot services. Genie is the app's core chat assistant,
so what matters is the **conversational output a user reads** — voice, personality
("does it feel like a real person"), helpfulness, speed, cost. Cost is secondary
here, so the matrix includes a **flagship (`claude-opus-4-8`)** alongside the
production model (`gemini-3.5-flash`), `gpt-5.6-terra`, and `claude-sonnet-5`.

```bash
npm run genie              # runs configs/genie-chat.yaml (15 realistic questions × 4 models)
npm run genie-transcript   # writes scorecard/genie-transcript.md — every reply side-by-side
npm run view               # or read them in promptfoo's web UI
```

- **What it measures:** the real Genie system prompt (`prompts/genie-chat.js` →
  `assistant-system.txt` + a mock saved-recipes context) against realistic asks
  (ingredient/vibe/constraint-driven, cooking Q&A, and a few multi-turn threads).
  **Tool-free** — it captures the conversational voice the user reads. The tool-calling
  *loop* (which tool, the `thought_signature` continuation) is the separate Phase-4
  rewrite; `assistant-tools.json` is extracted for that.
- **How to judge:** "feels human" is subjective, and an LLM judge favors its own
  family — so the judge here is **GPT-5.6 (non-Claude, since two candidates are Claude)**
  and its `genie_voice` score is only **directional**. The real decision comes from
  **reading `scorecard/genie-transcript.md`** — all four models' replies to each
  question, side by side, with speed + cost. Cross-check the rubric by swapping the
  judge to `google:gemini-3.5-flash` in `configs/genie-chat.yaml`.
- **Caveat:** this proxies the conversational layer, not the full tool-augmented
  production flow. For idea/Q&A asks the model answers inline (what the user sees);
  a "make it a full recipe" turn is handled by `create_recipe` in production.

## The decision

After a run, `scorecard/scorecard.md` holds the numbers and a go/no-go table.
Fill it in per service:

> Does any provider beat Gemini on **quality-adjusted cost** by enough to justify
> another SDK / key / billing account / failure mode? **"No" everywhere is a
> valid, money-saving outcome** — it means stop after Phase 0. "Yes" for a subset
> defines the entire scope of Phases 1–4.

## The decision

After a run, `scorecard/scorecard.md` holds the numbers and a go/no-go table.
Fill it in per service:

> Does any provider beat Gemini on **quality-adjusted cost** by enough to justify
> another SDK / key / billing account / failure mode? **"No" everywhere is a
> valid, money-saving outcome** — it means stop after Phase 0. "Yes" for a subset
> defines the entire scope of Phases 1–4.
