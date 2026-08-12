// Structured-tier assertions for nutrition estimation.
import { extractJson, res, fromChecks, macroReconcile } from "./lib.js";

const FIELDS = [
  "calories", "protein_g", "total_fat_g", "saturated_fat_g", "trans_fat_g",
  "cholesterol_mg", "sodium_mg", "total_carbs_g", "dietary_fiber_g", "total_sugars_g",
];

export function parses(output) {
  try { extractJson(output); return res(true, 1, "valid JSON"); }
  catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
}

export function schemaValid(output) {
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  const checks = FIELDS.map((f) => ({
    label: `${f} is number|null`,
    ok: f in d && (d[f] === null || (typeof d[f] === "number" && d[f] >= 0)),
  }));
  return fromChecks(checks);
}

// A useful estimate fills the core fields; report how complete it is.
export function completeness(output) {
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  const nonNull = FIELDS.filter((f) => typeof d[f] === "number").length;
  const core = ["calories", "protein_g", "total_fat_g", "total_carbs_g"];
  const coreOk = core.every((f) => typeof d[f] === "number");
  return res(coreOk, nonNull / FIELDS.length,
    `${nonNull}/${FIELDS.length} fields populated; core macros ${coreOk ? "present" : "MISSING"}`);
}

export function macroReconciliation(output) {
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  const r = macroReconcile(d, 25);
  if (r === null) return res(false, 0, "missing or non-numeric macros — cannot reconcile");
  return res(r.ok, r.ok ? 1 : 0, `4/4/9 est ${r.est.toFixed(0)} kcal vs stated ${d.calories} (${r.errPct.toFixed(0)}% off)`);
}

// Gross-error gate against a hand-set per-serving reference.
export function caloriesInBand(output, context) {
  const expected = Number(context?.vars?.expected_calories);
  const tolPct = Number(context?.vars?.calorie_tolerance_pct ?? 50);
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  if (typeof d.calories !== "number") return res(false, 0, "calories missing");
  if (!Number.isFinite(expected) || expected <= 0) return res(true, 1, "no reference set — skipped");
  const errPct = (Math.abs(d.calories - expected) / expected) * 100;
  const ok = errPct <= tolPct;
  return res(ok, ok ? 1 : 0, `${d.calories} kcal vs ref ~${expected} (${errPct.toFixed(0)}% off, tol ${tolPct}%)`);
}
