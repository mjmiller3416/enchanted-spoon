#!/usr/bin/env node
// Reads promptfoo per-service JSON results and writes scorecard/scorecard.md.
// Usage: node scorecard/generate.mjs [outputDir]   (default outputDir = ./output)
//
// Defensive about promptfoo's JSON shape across versions: it reads
// results.results[] and falls back through a few known layouts.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const outDir = process.argv[2] || path.join(here, "..", "output");
const scorecardPath = path.join(here, "scorecard.md");

const SERVICE_ORDER = [
  "cooking-tips", "recipe-generation", "recipe-import",
  "nutrition-estimation", "meal-suggestions",
];

function extractRows(data) {
  if (Array.isArray(data?.results?.results)) return data.results.results;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.results?.table?.body)) return data.results.table.body;
  return [];
}

function providerName(row) {
  const p = row.provider;
  if (!p) return "unknown";
  if (typeof p === "string") return p;
  return p.label || p.id || "unknown";
}

function rowMetrics(row) {
  const out = {};
  const cr = row.gradingResult?.componentResults;
  if (Array.isArray(cr) && cr.length) {
    for (const c of cr) {
      const name = c.assertion?.metric || c.assertion?.type;
      if (!name) continue;
      const score = typeof c.score === "number" ? c.score : c.pass ? 1 : 0;
      (out[name] ||= []).push(score);
    }
  }
  if (!Object.keys(out).length && row.namedScores) {
    for (const [k, v] of Object.entries(row.namedScores)) out[k] = [Number(v)];
  }
  // collapse each metric's list to its mean
  const flat = {};
  for (const [k, list] of Object.entries(out)) {
    flat[k] = list.reduce((a, b) => a + b, 0) / list.length;
  }
  return flat;
}

// A row is a real generation/API failure only if it produced no usable output.
// (promptfoo also sets row.error to the llm-rubric *reason text* when a rubric
// scores below threshold — that's an assertion outcome, not an API error.)
function isError(row) {
  const out = row.response?.output;
  const hasOutput = typeof out === "string" && out.trim().length > 0;
  if (hasOutput) return false;
  return Boolean(row.error || row.response?.error);
}

function pctl(sorted, p) {
  if (!sorted.length) return null;
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

function aggregate(rows) {
  // provider -> { n, errors, latencies[], costs[], tokens[], metrics: {name: []} }
  const byProvider = new Map();
  const order = [];
  for (const row of rows) {
    const name = providerName(row);
    if (!byProvider.has(name)) { byProvider.set(name, { n: 0, errors: 0, latencies: [], costs: [], tokens: [], metrics: {} }); order.push(name); }
    const agg = byProvider.get(name);
    agg.n++;
    if (isError(row)) agg.errors++;
    if (typeof row.latencyMs === "number") agg.latencies.push(row.latencyMs);
    if (typeof row.cost === "number") agg.costs.push(row.cost);
    const tok = row.response?.tokenUsage?.total ?? row.tokenUsage?.total;
    if (typeof tok === "number") agg.tokens.push(tok);
    for (const [m, v] of Object.entries(rowMetrics(row))) (agg.metrics[m] ||= []).push(v);
  }
  return { byProvider, order };
}

function tok(row) {
  const t = row.response?.tokenUsage || row.tokenUsage || {};
  const prompt = t.prompt ?? 0;
  const completion = t.completion ?? 0;
  const reasoning = t.completionDetails?.reasoning ?? 0;
  const total = t.total ?? prompt + completion + reasoning;
  return { prompt, completion, reasoning, total };
}

// Global per-provider usage rollup across all services (reconcile vs the $5 caps).
function usageSummary(rows) {
  const by = new Map();
  const order = [];
  for (const r of rows) {
    const name = providerName(r);
    if (!by.has(name)) { by.set(name, { calls: 0, prompt: 0, completion: 0, reasoning: 0, total: 0, cost: 0, priced: false }); order.push(name); }
    const a = by.get(name);
    const u = tok(r);
    a.calls++; a.prompt += u.prompt; a.completion += u.completion; a.reasoning += u.reasoning; a.total += u.total;
    if (typeof r.cost === "number") { a.cost += r.cost; if (r.cost > 0) a.priced = true; }
  }
  const head = ["Provider", "calls", "prompt tok", "answer tok", "thinking tok", "total tok", "total cost"];
  const lines = ["## Total usage per provider (all services)", "", `| ${head.join(" | ")} |`, `|${head.map(() => "---").join("|")}|`];
  for (const name of order) {
    const a = by.get(name);
    const cost = a.priced ? `$${a.cost.toFixed(4)}` : "unpriced¹";
    lines.push(`| ${name} | ${a.calls} | ${a.prompt} | ${a.completion} | ${a.reasoning} | ${a.total} | ${cost} |`);
  }
  const anyUnpriced = order.some((n) => !by.get(n).priced);
  let note = "_Reconcile against the $5-per-key caps. \"thinking tok\" is internal reasoning, billed as output (0 when thinking is disabled)._";
  if (anyUnpriced) note += " _¹ promptfoo 0.122 can't price every model (shown \"unpriced\"); multiply its total tokens by your provider rate._";
  lines.push("", note, "");
  return lines.join("\n");
}

function mean(a) { return a.length ? a.reduce((x, y) => x + y, 0) / a.length : null; }
function fmtPct(v) { return v == null ? "—" : `${Math.round(v * 100)}%`; }
function fmtMs(v) { return v == null ? "—" : `${Math.round(v)}ms`; }
function fmtCost(v) { return v == null ? "—" : `$${v.toFixed(5)}`; }
function fmtNum(v) { return v == null ? "—" : String(Math.round(v)); }

function renderService(service, rows) {
  const { byProvider, order } = aggregate(rows);
  if (!order.length) return `### ${service}\n\n_No results found in output JSON._\n`;

  // Union of metric names across providers, in stable-ish order.
  const metricNames = [];
  for (const name of order) {
    for (const m of Object.keys(byProvider.get(name).metrics)) if (!metricNames.includes(m)) metricNames.push(m);
  }

  const header = ["Provider", "n", "error%", ...metricNames.map((m) => `${m} %`), "lat p50", "lat p95", "cost/call", "avg tok"];
  const lines = [`### ${service}`, "", `| ${header.join(" | ")} |`, `|${header.map(() => "---").join("|")}|`];

  for (const name of order) {
    const a = byProvider.get(name);
    const lat = [...a.latencies].sort((x, y) => x - y);
    const cells = [
      name,
      String(a.n),
      a.n ? `${Math.round((a.errors / a.n) * 100)}%` : "—",
      ...metricNames.map((m) => fmtPct(mean(a.metrics[m] || []))),
      fmtMs(pctl(lat, 50)),
      fmtMs(pctl(lat, 95)),
      fmtCost(mean(a.costs)),
      fmtNum(mean(a.tokens)),
    ];
    lines.push(`| ${cells.join(" | ")} |`);
  }
  lines.push("");
  // Flag the malformed-JSON rate explicitly for structured services.
  if (metricNames.includes("json_parse")) {
    const notes = order.map((name) => {
      const j = mean(byProvider.get(name).metrics.json_parse || []);
      return j == null ? null : `${name}: ${Math.round((1 - j) * 100)}% malformed-JSON`;
    }).filter(Boolean);
    if (notes.length) lines.push(`_Malformed-JSON rate — ${notes.join(" · ")}_`, "");
  }
  return lines.join("\n");
}

// ── Load per-service JSON files ─────────────────────────────────────────────
if (!fs.existsSync(outDir)) {
  console.error(`No output dir at ${outDir}. Run the eval first (npm run all).`);
  process.exit(1);
}
const files = fs.readdirSync(outDir).filter((f) => f.endsWith(".json"));
if (!files.length) {
  console.error(`No .json result files in ${outDir}. Run the eval first (npm run all).`);
  process.exit(1);
}

const sections = [];
const seen = [];
const allRows = [];
const ordered = [
  ...SERVICE_ORDER.filter((s) => files.includes(`${s}.json`)).map((s) => `${s}.json`),
  ...files.filter((f) => !SERVICE_ORDER.includes(f.replace(/\.json$/, ""))),
];
for (const file of ordered) {
  const service = file.replace(/\.json$/, "");
  let data;
  try { data = JSON.parse(fs.readFileSync(path.join(outDir, file), "utf8")); }
  catch (e) { sections.push(`### ${service}\n\n_Could not parse ${file}: ${e.message}_\n`); continue; }
  const rows = extractRows(data);
  allRows.push(...rows);
  sections.push(renderService(service, rows));
  seen.push(service);
}

const generatedAt = process.env.SCORECARD_TIMESTAMP || "(set SCORECARD_TIMESTAMP or fill in the run date)";
const body = `# Whiskful AI Provider Scorecard (Phase 0)

_Generated from: ${seen.join(", ") || "no services"}._
_Run date: ${generatedAt}_

> Auto-generated by \`scorecard/generate.mjs\`. Scores are 0–100% (assertion pass
> rate or judge score). **Weight the columns by the service's real job** — see the
> weighting guide at the bottom. For open-ended services, \`*_quality\` is the LLM
> judge's absolute rubric score (ranking is read from these); it carries the
> self-preference caveat in the README.

${usageSummary(allRows)}
${sections.join("\n")}

---

## Weighting guide

- **Cooking tips, meal suggestions** → cost & latency dominate; quality bar is "good + varied".
- **Recipe generation, nutrition, import** → quality/correctness dominate (\`schema_valid\`,
  \`macro_reconcile\`, \`ingredient_fidelity\`, \`calories_in_band\`).
- A cheaper model that loses slightly on quality can still be the right call for tips.

## Go / no-go (fill in per service)

For each service: does any provider beat Gemini on **quality-adjusted cost** by
enough to justify the added operational surface (another SDK, key, billing account,
failure mode)? Record the decision:

| Service | Winner (data) | Beats Gemini enough to switch? | Decision |
|---|---|---|---|
| Cooking tips | | | |
| Recipe generation | | | |
| Recipe import | | | |
| Nutrition estimation | | | |
| Meal suggestions | | | |

**"No" everywhere is a valid, money-saving outcome** — it means stop after Phase 0.
"Yes" for a subset defines the entire scope of Phases 1–4.
`;

fs.writeFileSync(scorecardPath, body);
console.error(`Wrote ${path.relative(process.cwd(), scorecardPath)} (${seen.length} services).`);
