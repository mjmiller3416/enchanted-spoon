// Shared helpers for the structured-tier assertions.
// ESM (package.json has "type":"module"). promptfoo resolves `file://x.js:fn`.

// Mirror the app's JSON tolerance so the eval measures the model the way the
// service actually consumes it: direct parse → strip markdown fences → decode
// the first complete {...} object (nutrition_estimation.py:_extract_json +
// recipe_import raw_decode fallback).
export function extractJson(text) {
  if (text == null) throw new Error("empty output");
  const s = String(text).trim();
  if (!s) throw new Error("empty output");

  try { return JSON.parse(s); } catch { /* fall through */ }

  const unfenced = s.replace(/```(?:json)?\s*/gi, "").replace(/```\s*$/g, "").trim();
  try { return JSON.parse(unfenced); } catch { /* fall through */ }

  // Brace-matched first object, string-aware (handles braces inside strings).
  const start = s.indexOf("{");
  if (start !== -1) {
    let depth = 0, inStr = false, esc = false;
    for (let i = start; i < s.length; i++) {
      const c = s[i];
      if (inStr) {
        if (esc) esc = false;
        else if (c === "\\") esc = true;
        else if (c === '"') inStr = false;
      } else if (c === '"') inStr = true;
      else if (c === "{") depth++;
      else if (c === "}") {
        depth--;
        if (depth === 0) return JSON.parse(s.slice(start, i + 1));
      }
    }
  }
  throw new Error("no valid JSON object found");
}

// Enums, kept in lockstep with the service prompts / DTOs.
export const CATEGORIES = ["american", "chinese", "french", "indian", "italian", "japanese", "mediterranean", "mexican", "thai", "other"];
export const MEAL_TYPES = ["appetizer", "breakfast", "lunch", "dinner", "dessert", "side", "snack", "sauce", "other"];
export const DIET_PREFS = ["none", "vegetarian", "vegan", "gluten-free", "dairy-free", "keto", "paleo"];
export const INGREDIENT_CATEGORIES = ["produce", "dairy", "deli", "meat", "condiments", "oils-and-vinegars", "seafood", "pantry", "spices", "frozen", "bakery", "baking", "beverages", "other"];
export const UNITS = ["tbs", "tsp", "cup", "oz", "lbs", "stick", "bag", "box", "can", "jar", "package", "piece", "slice", "whole", "pinch", "dash", "to-taste"];
export const DIFFICULTY = ["Easy", "Medium", "Hard"];

export function isNonEmptyString(v) {
  return typeof v === "string" && v.trim().length > 0;
}

export function res(pass, score, reason) {
  return { pass, score: score == null ? (pass ? 1 : 0) : score, reason };
}

// Roll a list of {ok, label} checks into one GradingResult. pass = all critical
// checks ok; score = fraction ok (partial-credit visibility in the scorecard).
export function fromChecks(checks, { passThreshold = 1 } = {}) {
  const total = checks.length;
  const okCount = checks.filter((c) => c.ok).length;
  const score = total === 0 ? 1 : okCount / total;
  const failed = checks.filter((c) => !c.ok).map((c) => c.label);
  const pass = score >= passThreshold;
  const reason = failed.length ? `failed: ${failed.join("; ")}` : "all checks passed";
  return res(pass, score, reason);
}

// 4/4/9 rule: protein & carbs 4 kcal/g, fat 9 kcal/g. Returns null when the
// inputs needed for the check are missing.
export function macroReconcile(n, tolerancePct = 25) {
  if (!n) return null;
  const { calories, protein_g, total_fat_g, total_carbs_g } = n;
  if ([calories, protein_g, total_fat_g, total_carbs_g].some((v) => typeof v !== "number")) return null;
  if (calories <= 0) return null;
  const est = 4 * protein_g + 4 * total_carbs_g + 9 * total_fat_g;
  const errPct = (Math.abs(est - calories) / calories) * 100;
  return { est, errPct, ok: errPct <= tolerancePct };
}
