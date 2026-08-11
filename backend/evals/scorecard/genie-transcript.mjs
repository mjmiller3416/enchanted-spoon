#!/usr/bin/env node
// Reads output/genie-chat.json and writes scorecard/genie-transcript.md — every
// question with all models' replies side by side (+ voice score, latency, cost) so
// the "feels like a real person" call can be made by reading, not by trusting a judge.
// Usage: node scorecard/genie-transcript.mjs [output/genie-chat.json]
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const inPath = process.argv[2] || path.join(here, "..", "output", "genie-chat.json");
const outPath = path.join(here, "genie-transcript.md");

if (!fs.existsSync(inPath)) {
  console.error(`No results at ${inPath}. Run: npm run genie`);
  process.exit(1);
}
const data = JSON.parse(fs.readFileSync(inPath, "utf8"));
const rows = data?.results?.results || data?.results || [];

const prov = (r) => (typeof r.provider === "string" ? r.provider : r.provider?.label || r.provider?.id || "?");
const metric = (r, name) => {
  const c = (r.gradingResult?.componentResults || []).find((x) => x.assertion?.metric === name);
  return c ? c.score : null;
};
const lastUser = (r) => {
  const msgs = r.vars?.messages || r.testCase?.vars?.messages || [];
  const u = [...msgs].reverse().find((m) => m.role === "user");
  return u?.content || "(question)";
};
const desc = (r) => r.testCase?.description || r.description || "";
const isMultiTurn = (r) => ((r.vars?.messages || r.testCase?.vars?.messages || []).length > 1);

// group by test (description + question), preserve first-seen order
const groups = new Map();
for (const r of rows) {
  const key = desc(r) || lastUser(r);
  if (!groups.has(key)) groups.set(key, []);
  groups.get(key).push(r);
}

// per-provider summary
const summ = new Map();
const order = [];
for (const r of rows) {
  const p = prov(r);
  if (!summ.has(p)) { summ.set(p, { n: 0, voice: [], fmt: [], lat: [], cost: [] }); order.push(p); }
  const s = summ.get(p);
  s.n++;
  const v = metric(r, "genie_voice"); if (v != null) s.voice.push(v);
  const f = metric(r, "format_ok"); if (f != null) s.fmt.push(f);
  if (typeof r.latencyMs === "number") s.lat.push(r.latencyMs);
  if (typeof r.cost === "number") s.cost.push(r.cost);
}
const mean = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : null);
const p50 = (a) => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
const pct = (v) => (v == null ? "—" : `${Math.round(v * 100)}%`);
const ms = (v) => (v == null ? "—" : `${Math.round(v)}ms`);
const usd = (v) => (v == null ? "—" : v > 0 ? `$${v.toFixed(5)}` : "unpriced");

const out = [];
out.push("# Genie chat bake-off — transcript", "");
out.push("> Read the replies and decide which model *feels* like Genie. The `voice`");
out.push("> score is a directional LLM-rubric grade (GPT-5.6 judge), not the final word.", "");
out.push("## Summary (per model)", "");
out.push("| Model | voice (rubric) | format_ok | latency p50 | cost/call |");
out.push("|---|---|---|---|---|");
for (const p of order) {
  const s = summ.get(p);
  out.push(`| ${p} | ${pct(mean(s.voice))} | ${pct(mean(s.fmt))} | ${ms(p50(s.lat))} | ${usd(mean(s.cost))} |`);
}
out.push("");
out.push("---", "");

let i = 0;
for (const [key, rs] of groups) {
  i++;
  const mt = isMultiTurn(rs[0]);
  out.push(`## ${i}. ${key}${mt ? "  _(multi-turn)_" : ""}`, "");
  out.push(`**User:** ${lastUser(rs[0])}`, "");
  // stable provider order
  rs.sort((a, b) => order.indexOf(prov(a)) - order.indexOf(prov(b)));
  for (const r of rs) {
    const v = metric(r, "genie_voice");
    out.push(`### ${prov(r)} — voice ${pct(v)} · ${ms(r.latencyMs)} · ${usd(r.cost)}`, "");
    out.push(String(r.response?.output || r.error || "(no output)").trim(), "");
  }
  out.push("---", "");
}

fs.writeFileSync(outPath, out.join("\n"));
console.error(`Wrote ${path.relative(process.cwd(), outPath)} (${groups.size} questions, ${rows.length} replies).`);
