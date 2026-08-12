# AI Gateway & Provider Evaluation

Plan drafted August 2026 from a read of the current `backend/app/services/ai/` module. Not a
build prompt — read each phase before starting it, and note that the single most important
gate in this whole plan (**DECISION** after Phase 0) is "should we even do this?" The honest
answer might be no, and that's a *successful* outcome of Phase 0, not a failure.

> **Where this fits:** the [public-release-roadmap](public-release-roadmap.md)'s Phase 5 ("AI
> feature completeness") and the monetization work both depend on AI unit economics — cost per
> call directly sets the margin between the ~$3.94/mo a heavy user costs today and the $4.99
> Pro price. This plan produces the per-provider, per-service cost/quality numbers that turn
> that margin from a guess into a measurement. It does **not** duplicate the usage-metering
> work (already shipped in the roadmap's Phase 0); it consumes it.

## Why this exists

Two things are true at once: (1) model quality and price move every few weeks now, and being
locked to one vendor's SDK means every "is X better for task Y?" question is unanswerable
without a code change; (2) the app is cost-sensitive at exactly the AI layer that drives its
margin. A provider-agnostic seam plus a repeatable eval turns "I think OpenAI might be better
at recipe generation" into a number you can defend — and lets you re-ask the question cheaply
every time a new model drops.

**The core reframe that shapes every phase:** the gateway and the eval are the same project.
The reason to build the abstraction is not vague "flexibility" — it's that a clean seam is the
only way to run an apples-to-apples comparison and *keep* running it. So this plan builds the
**ruler before the cut**: Phase 0 measures whether a switch is even worth it, *before* any
refactor. If Gemini wins on quality-adjusted cost across the board, we stop after Phase 0
having spent a few days instead of committing to a multi-week migration.

## What the code looks like today

You are much closer to this than a green-field project — the seam already exists in spirit:

- `gemini_client.py:30-67` — one client factory, keyed by API key, already with bounded
  timeout + capped-exponential-backoff retry. This is the natural home for the abstraction.
- `config.py` — model names already centralized behind env vars (`GEMINI_MODEL`,
  `GEMINI_ASSISTANT_MODEL`, `GEMINI_IMAGE_MODEL`).
- `response_utils.py` — `extract_text_from_response` / `extract_image_data`. **Provider-coupled**:
  both walk Gemini's `candidates[].content.parts[]` shape. These become adapter internals.
- Every text service calls the same shape: `client.models.generate_content(model, contents, config)`.

The services split into **two tiers of migration difficulty**, and the entire risk of this
project lives in not conflating them:

| Tier | Services | Shape | Migration cost |
|---|---|---|---|
| **1 — trivial** | cooking tips, recipe generation, nutrition estimation, meal suggestions, recipe import | single-shot: prompt → text/JSON | A config change once the seam exists. `complete(model, messages, json_schema?)` covers all five. |
| **2 — hard** | the assistant (Genie chat) | multi-turn + function calling | **A rewrite of the tool-calling loop, not a model swap.** See landmine #1. |
| **separate** | image generation | prompt → image bytes | Different interface entirely (not `complete()`); different output contract per provider. |

## The three non-obvious costs (read before scoping)

**Landmine #1 — the assistant's tool-calling loop is provider-specific.**
`assistant/service.py:150-214` captures `model_turn` specifically to replay Gemini 3.x's
`thought_signature` on the function-call continuation (lines 180-205; there's a standing
memory note about this — a follow-up call that drops the signature fails with
`MALFORMED_FUNCTION_CALL`). **None of this translates to OpenAI or Claude.** Their tool loops
are different protocols entirely: an assistant message carrying `tool_calls`, then `tool`-role
result messages, no thought signatures. Moving "Genie Chat → GPT" (as the diagram shows) means
reimplementing the continuation loop per provider — this is Phase 4, deliberately last and
deliberately gated on Phase 3 actually showing a non-Gemini win for chat.

**Landmine #2 — image generation diverges more than text.**
`extract_image_data` (`response_utils.py:33-57`) reads Gemini's inline `base64`/`bytes`. OpenAI's
image models return a different envelope (`b64_json` / URL), and quality/style differ enough
that this is a *taste* call, not a quality-metric call. The diagram keeps images on Gemini,
which is the right default. Image gets its own thin interface and the lowest priority.

**Landmine #3 — per-service API keys are load-bearing.**
Each service reads its own key today (`GEMINI_TIP_API_KEY`, `GEMINI_RECIPE_GENERATION_API_KEY`,
`GEMINI_ASSISTANT_API_KEY`, `GEMINI_IMAGE_API_KEY`, `GEMINI_NUTRITION_API_KEY`) — likely for
quota isolation and per-feature billing attribution. The abstraction must preserve
per-(provider, service) key resolution, not collapse to one global key, or you lose that
attribution right when the eval needs it most.

## Status tracker

| Phase | Focus | Depends on | Status |
|---|---|---|---|
| [0](#phase-0--eval-harness-first-the-ruler) | Offline eval harness + go/no-go decision | — | ✅ **DONE (2026-08-11) — DECISION: NO-GO, stay on Gemini 3.5-flash** |
| [1](#phase-1--the-provider-seam) | The provider seam (`LLMClient` + Gemini adapter) | Phase 0 says "go" | Not needed¹ |
| [2](#phase-2--add-providers) | Add OpenAI (+ Claude) adapters, config-driven routing | Phase 1 | Not needed¹ |
| [3](#phase-3--in-app-validation--rollout) | Shadow/canary in-app, decide routing per service | Phase 2 | Not needed¹ |
| [4](#phase-4--the-assistant-migration-hard-tier) | Assistant/function-calling migration | Phase 3 shows a chat win | Not needed¹ |
| [5](#phase-5--ops-observability-cost-fallback-continuous-eval) | Observability, cost tracking, fallback, continuous eval | Phase 2 | Optional — GPT-5.6 Terra validated as fallback |

Phase 0 is a hard gate — nothing after it is justified until its numbers exist. Phase 5 can
begin in parallel with Phase 3 once the seam (Phase 1) is in.

> **¹ Phase 0 outcome (harness at `backend/evals/`, full writeup in
> `backend/evals/scorecard/findings.md`):** against the real production config
> (`gemini-3.5-flash`, thinking disabled), Gemini is the **fastest and cheapest**
> provider on all five services with competitive-to-best quality — GPT-5.6 Terra and
> Claude Sonnet 5 don't beat it on quality-adjusted cost anywhere. So Phases 1–4 are
> **not justified**; the project succeeded by saving the refactor. Two follow-ups:
> (a) **do not adopt `gemini-3.6-flash`** — it can't disable thinking, making it
> slower/heavier and prone to truncating structured JSON (its exploratory scorecard
> is archived at `backend/evals/scorecard/scorecard-gemini-3.6.md`); (b) Gemini's
> occasional malformed JSON on recipe-generation (13%) + nutrition (17%) is the only
> soft spot — already mitigated in-app by `_extract_json`/retry; if prod telemetry
> shows it's user-impacting, scope a *targeted* switch of just those two services to
> GPT-5.6 Terra (the cheapest 0%-malformed option). Keep GPT-5.6 as the Phase-5 fallback.

## Guiding principles & non-goals

- **Measure before refactoring.** No adapter code until Phase 0 numbers exist.
- **Route per task, from data — not from the diagram.** The diagram's assignments
  (Genie→GPT, Recipe Gen→GPT, Import/Tips/Images→Gemini) are a *hypothesis to test*, not a
  plan to implement.
- **Weight metrics by the service's real job.** Tips are latency- and cost-dominated (shown on
  load, quality bar is "good + varied"); recipe gen and chat are quality-dominated (the "wow"
  features). A cheap model that loses slightly on quality can still be the right call for tips.
- **Non-goal:** a heavyweight SaaS control plane. At this scale a thin internal seam (+ optional
  self-hosted LiteLLM in Phase 5) beats Braintrust/LangSmith/Portkey.
- **Non-goal:** rewriting prompts. Phase 0 *extracts* the existing prompts verbatim so the eval
  measures the providers, not a prompt change. Prompt tuning is a separate effort.

---

## Phase 0 — Eval harness first (the ruler)

Goal: answer "is switching any service off Gemini worth it?" **before** touching the app.
promptfoo can call Gemini/OpenAI/Claude directly with your prompts — it does **not** need the
app abstraction — so this phase de-risks everything after it and can outright cancel the
project.

- [ ] **Stand up [promptfoo](https://promptfoo.dev) as the harness.** Declarative provider
      matrix (Gemini + OpenAI + Claude native), built-in assertions incl. `llm-rubric`,
      side-by-side web view, per-run cost tracking. Lives alongside `backend/tests/` (e.g.
      `backend/evals/`). No app code touched.
- [ ] **Extract the real prompts into eval configs.** Pull the actual templates so the eval
      measures providers, not a rewrite: `cooking_tips.py:70-79` (TIP_PROMPT_TEMPLATE),
      `recipe_generation/config.py` (PROMPT_TEMPLATE + NUTRITION_SCHEMA), the recipe-import and
      nutrition prompts, and the assistant system prompt + `TOOL_DEFINITIONS`. Surfacing that
      prompts are scattered across service modules is itself a useful outcome.
- [ ] **Build golden datasets per service.** For structured services, hand-label expected
      output: recipe-gen prompts; import source URLs/text with expected extracted fields;
      nutrition inputs. For open-ended services (tips, meal suggestions), a representative
      input set is enough — those are judged, not diffed.
- [ ] **Programmatic checks for the structured tier (your strongest, cheapest signal).**
      JSON parses? matches the DTO schema (`RecipeGeneratedDTO`, `NutritionFactsDTO`)?
      quantities sane? nutrition macros reconcile with calories (4/4/9 rule)? import
      field-extraction accuracy vs. ground truth? Encode these as promptfoo assertions and run
      the identical inputs through each provider.
- [ ] **Pairwise LLM-as-judge for the open-ended tier.** Blind A/B ("which tip is better?") —
      pairwise win-rate is far more reliable than absolute 1–10 scoring. **Use a different model
      family as the judge** (e.g. Claude judging GPT-vs-Gemini) to avoid self-preference bias.
- [ ] **Capture the full scorecard, not just quality.** Per provider × service: quality
      (checks + judge win-rate), **latency p50/p95**, **cost/call** (tokens × price),
      reliability (error + malformed-JSON + refusal rate), consistency (variance over repeated
      runs). Schema in the [appendix](#appendix--the-scorecard).
- [ ] **Include Claude in the matrix.** Adding a column is free in promptfoo and it's strong at
      exactly this workload (structured/JSON output, instruction-following, tool use). Let the
      data, not intuition, keep or drop it.
- [ ] **DECISION — go/no-go, per service.** With the scorecard in hand: for each service, does
      any provider beat Gemini on *quality-adjusted cost* by enough to justify operational
      surface (another SDK, key, billing account, failure mode)? If the answer is "no"
      everywhere → **stop here**; the project succeeded by saving the refactor. If "yes" for
      some subset → that subset, and only that subset, defines the scope of Phases 1–4.

**Exit criteria:** a committed scorecard in `backend/evals/` and a written go/no-go per service.

---

## Phase 1 — The provider seam

Only if Phase 0 says "go." Generalize the client you already have into a provider-agnostic
interface, then migrate the **Tier-1 services** behind it. Prove it with one service before
touching the rest.

- [ ] **Define the interface.** A narrow port covering the single-shot case, plus a normalized
      response so callers stop touching Gemini's `parts[]` shape directly:

      ```python
      class LLMClient(Protocol):
          def complete(self, *, model: str, messages: list[Message],
                       response_format: ResponseFormat | None = None,
                       temperature: float | None = None,
                       max_tokens: int | None = None) -> LLMResponse: ...

      # LLMResponse: text | structured payload, usage (prompt/completion tokens),
      #              finish_reason, and .raw for escape hatches.
      ```

      The assistant's multi-turn + tool loop is **out of scope here** — it gets its own
      interface in Phase 4. Don't force one method to serve both.
- [ ] **Write the Gemini adapter by wrapping existing code.** It should call the current
      `get_gemini_client()` (`gemini_client.py:30-67`, keeping the timeout/retry) and fold in
      `extract_text_from_response`. Net behavior identical — this is a refactor, not a change.
- [ ] **Preserve per-(provider, service) key resolution** (landmine #3). Key lookup stays
      per-service so billing attribution and quota isolation survive.
- [ ] **Migrate one service as the proof: cooking tips.** Smallest surface
      (`cooking_tips.py:144-152` is the only call site), and its dedup/rotation logic stays
      untouched above the seam. Confirm parity, then migrate recipe generation, nutrition,
      meal suggestions, and import.
- [ ] **Keep the tests green.** `tests/test_recipe_generation_service.py` and
      `tests/test_nutrition_service.py` already exercise these paths (mind the known async-mock
      baseline); update mocks to target the seam, not `genai` directly.

**Exit criteria:** all five Tier-1 services call `LLMClient.complete()`; Gemini adapter is the
only implementation; behavior unchanged; tests green.

---

## Phase 2 — Add providers

- [ ] **Implement the OpenAI adapter** against the same `LLMClient` interface — including
      `response_format`/JSON-mode mapping so the structured services get schema-valid output.
- [ ] **Implement the Claude adapter** if Phase 0 kept it in scope.
- [ ] **Config-driven provider selection per service.** Extend `config.py` from
      `GEMINI_*_MODEL` to a per-service `{provider, model}` resolution (env-overridable), so
      routing is configuration, not code. This is the machinery the diagram was really asking
      for.
- [ ] **Re-point the Phase 0 eval at the seam** so the same harness now runs through real app
      code paths, not just promptfoo's direct calls — catches integration-level differences
      (JSON-mode quirks, token accounting) the offline eval can miss.

**Exit criteria:** any Tier-1 service can be pointed at Gemini, OpenAI, or Claude by config
alone, with no code change.

---

## Phase 3 — In-app validation & rollout

Phase 0 was "could another provider win, in principle." This is "does it win in production
conditions, and let's flip it safely."

- [ ] **Shadow or canary the candidate provider** for each service Phase 0 flagged: run the new
      provider on a fraction of real traffic (or replay logged inputs offline) and compare
      against Gemini on the live scorecard metrics.
- [ ] **Confirm prod-condition parity** — latency under real load, cost at real token volumes,
      error/refusal rates on real inputs (not the curated golden set).
- [ ] **DECISION — final routing, per service.** Commit the winning `{provider, model}` per
      service. Expect a *mix* (route by task); that's normal and fine. Update the eval scorecard
      with the chosen config as the new baseline.
- [ ] **Feed the numbers back to monetization.** The per-call cost from the chosen routing is
      the real input to the Pro-tier margin question in the release roadmap.

**Exit criteria:** each Tier-1 service is on its data-chosen provider in production; routing is
recorded.

---

## Phase 4 — The assistant migration (hard tier)

**Only if Phase 3 shows a real chat win off Gemini.** This is the rewrite, not a swap — budget
for it accordingly (landmine #1).

- [ ] **Model the tool loop as a provider-specific strategy** behind a common `ChatSession`
      interface — distinct from `complete()`. One code path must not pretend to handle both
      protocols.
- [ ] **Gemini strategy: preserve the `thought_signature` replay** exactly as it works today
      (`assistant/service.py:180-205`). Do not "clean it up" during the abstraction — it's
      load-bearing.
- [ ] **OpenAI/Claude strategy: implement their native tool loop** — assistant message with
      `tool_calls` → execute → `tool`-role result messages → continue. Re-map `TOOL_DEFINITIONS`
      to each provider's function-schema format.
- [ ] **Port the response reconciliation.** The preamble-vs-function-call precedence logic
      (`service.py:162-214`) is Gemini-specific; each provider needs its own equivalent so a
      tool call always beats conversational preamble.
- [ ] **Eval chat specifically.** Multi-turn tool-selection accuracy is its own metric — does
      the model call the *right* tool with the *right* args? Judge on task completion, not just
      reply text.

**Exit criteria:** Genie chat runs on the chosen provider with tool calling at parity or
better; the Gemini strategy remains available via config.

---

## Phase 5 — Ops: observability, cost, fallback, continuous eval

Can start alongside Phase 3 once the seam exists. Optional but this is what makes the whole
thing durable instead of a one-time bake-off.

- [ ] **Per-request cost + latency logging** at the seam (provider, model, service, tokens,
      ms, outcome). This is the raw material for both the margin analysis and for building eval
      sets from *real* traffic (far stronger than synthetic prompts).
- [ ] **Consider self-hosted [LiteLLM](https://github.com/BerriAI/litellm)** as the proxy
      flavor of gateway: OpenAI-compatible, runs on Railway, unified format + cost tracking +
      provider fallback out of the box. Weigh it against keeping direct SDK adapters — adopt
      only if the fallback/logging pays for the extra hop. (Ties to the observability gap
      deferred in the release roadmap's Phase 3.)
- [ ] **Provider fallback.** If the primary provider 5xx's or times out past the retry budget,
      fall back to a secondary (e.g. Gemini ↔ OpenAI) for that call. The seam is the place for
      this.
- [ ] **Make the eval re-runnable on demand.** A single command that regenerates the scorecard
      across all providers, so "does the new model beat our current routing?" is a 20-minute
      question every time a model drops — the original justification for the whole project.

**Exit criteria:** cost/latency observable per call; the scorecard regenerates with one command.

---

## Open decisions (consolidated)

| # | Decision | Phase | Notes |
|---|---|---|---|
| D1 | **Is any switch worth it, per service?** | 0 | ✅ **RESOLVED: NO — stay on Gemini 3.5-flash everywhere.** It's fastest + cheapest on all 5 with competitive quality (`backend/evals/scorecard/findings.md`). Only soft spot: malformed structured JSON on recipe-gen/nutrition (already mitigated in-app) → targeted GPT-5.6 switch only if telemetry shows user impact. |
| D2 | Keep Claude in the provider matrix? | 0 | ✅ Included. Sonnet 5 matched on quality but was slowest + priciest — not the challenger to beat; GPT-5.6 Terra was. |
| D3 | Final routing (provider+model) per service | 3 | Moot given D1 = no switch. Baseline stays: `gemini-3.5-flash` per service (current prod). |
| D4 | Migrate the assistant off Gemini at all? | 4 | No — gated on a chat win that D1 didn't produce. |
| D5 | Adopt LiteLLM proxy vs. direct SDK adapters? | 5 | Adopt only if fallback + unified logging earn the extra hop. |

## Appendix — the scorecard

The artifact Phase 0 produces and Phase 5 keeps re-generating. One row per (service × provider);
weight the columns by the service's real job (see principles).

| Service | Provider / model | Quality (checks % / judge win-rate) | Latency p50 / p95 | Cost / call | Error % | Malformed-JSON % | Consistency (variance) |
|---|---|---|---|---|---|---|---|
| Cooking tips | … | … | … | … | … | n/a | … |
| Recipe generation | … | … | … | … | … | … | … |
| Recipe import | … | … | … | … | … | … | … |
| Nutrition estimation | … | … | … | … | … | … | … |
| Meal suggestions | … | … | … | … | … | … | … |
| Assistant (chat) | … | tool-selection accuracy | … | … | … | … | … |
| Image generation | … | human spot-check only | … | … | … | n/a | n/a |

**Weighting guide:** tips & images → cost/latency dominate; recipe gen, import, nutrition →
quality/correctness dominate; assistant → tool-selection accuracy dominates.
