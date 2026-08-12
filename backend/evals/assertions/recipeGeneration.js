// Structured-tier assertions for recipe generation.
// Each export is a separate promptfoo assertion (own `metric:`), so the scorecard
// gets clean per-dimension rates. Referenced as file://../assertions/recipeGeneration.js:fn
import {
  extractJson, CATEGORIES, MEAL_TYPES, DIET_PREFS, INGREDIENT_CATEGORIES, UNITS,
  DIFFICULTY, isNonEmptyString, res, fromChecks, macroReconcile,
} from "./lib.js";

export function parses(output) {
  try { extractJson(output); return res(true, 1, "valid JSON"); }
  catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
}

export function schemaValid(output) {
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }

  const ings = Array.isArray(d.ingredients) ? d.ingredients : [];
  const checks = [
    { label: "recipe_name non-empty", ok: isNonEmptyString(d.recipe_name) },
    { label: "recipe_category in enum", ok: CATEGORIES.includes(d.recipe_category) },
    { label: "meal_type in enum", ok: MEAL_TYPES.includes(d.meal_type) },
    { label: "diet_pref in enum", ok: DIET_PREFS.includes(d.diet_pref) },
    { label: "difficulty in enum", ok: DIFFICULTY.includes(d.difficulty) },
    { label: "6-15 ingredients", ok: ings.length >= 6 && ings.length <= 15 },
    { label: "directions non-empty", ok: isNonEmptyString(d.directions) },
    { label: "all ingredient_name non-empty", ok: ings.length > 0 && ings.every((i) => isNonEmptyString(i.ingredient_name)) },
    { label: "all ingredient_category in enum", ok: ings.length > 0 && ings.every((i) => INGREDIENT_CATEGORIES.includes(i.ingredient_category)) },
    { label: "all units in enum", ok: ings.length > 0 && ings.every((i) => UNITS.includes(i.unit)) },
  ];
  return fromChecks(checks);
}

export function directionsSteps(output) {
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  const steps = String(d.directions || "").split(/\n|\r/).map((s) => s.trim()).filter(Boolean);
  const ok = steps.length >= 5 && steps.length <= 10;
  return res(ok, ok ? 1 : 0, `${steps.length} direction steps (want 5-10)`);
}

export function quantitiesSane(output) {
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  const ings = Array.isArray(d.ingredients) ? d.ingredients : [];
  if (!ings.length) return res(false, 0, "no ingredients");
  const bad = ings.filter((i) => !(typeof i.quantity === "number" && i.quantity > 0 && i.quantity < 1000));
  const ok = bad.length === 0;
  return res(ok, ok ? 1 : 1 - bad.length / ings.length,
    ok ? "all quantities sane" : `${bad.length}/${ings.length} quantities missing/out-of-range`);
}

export function macroReconciliation(output, context) {
  const expect = context?.vars?.expect_nutrition;
  if (!expect) return res(true, 1, "n/a (nutrition not requested)");
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  const r = macroReconcile(d.nutrition_facts, 25);
  if (r === null) return res(false, 0, "nutrition_facts missing or non-numeric macros");
  return res(r.ok, r.ok ? 1 : 0, `4/4/9 est ${r.est.toFixed(0)} kcal vs stated ${d.nutrition_facts.calories} (${r.errPct.toFixed(0)}% off)`);
}
