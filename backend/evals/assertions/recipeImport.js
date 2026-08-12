// Structured-tier assertions for recipe import (faithful normalization).
import {
  extractJson, CATEGORIES, MEAL_TYPES, DIET_PREFS, INGREDIENT_CATEGORIES, UNITS,
  isNonEmptyString, res, fromChecks,
} from "./lib.js";

function isNoRecipe(d) {
  return d && d.no_recipe_found === true;
}

export function parses(output) {
  try { extractJson(output); return res(true, 1, "valid JSON"); }
  catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
}

// Correct routing: no-recipe pages must return exactly {no_recipe_found:true};
// recipe pages must NOT claim no_recipe_found.
export function noRecipeHandled(output, context) {
  const expectNo = context?.vars?.expect_no_recipe === true;
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  if (expectNo) {
    const ok = isNoRecipe(d) && !Array.isArray(d.ingredients);
    return res(ok, ok ? 1 : 0, ok ? "correctly flagged no_recipe_found" : "should have returned {no_recipe_found:true}");
  }
  const ok = !isNoRecipe(d);
  return res(ok, ok ? 1 : 0, ok ? "recipe returned as expected" : "wrongly returned no_recipe_found for a real recipe");
}

export function schemaValid(output, context) {
  if (context?.vars?.expect_no_recipe === true) return res(true, 1, "n/a (no-recipe page)");
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  if (isNoRecipe(d)) return res(false, 0, "returned no_recipe_found for a real recipe");

  const ings = Array.isArray(d.ingredients) ? d.ingredients : [];
  // Import allows quantity/unit to be null (unlike generation).
  const checks = [
    { label: "recipe_name non-empty", ok: isNonEmptyString(d.recipe_name) },
    { label: "recipe_category in enum", ok: CATEGORIES.includes(d.recipe_category) },
    { label: "meal_type in enum", ok: MEAL_TYPES.includes(d.meal_type) },
    { label: "diet_pref in enum", ok: DIET_PREFS.includes(d.diet_pref) },
    { label: "has ingredients", ok: ings.length > 0 },
    { label: "directions non-empty", ok: isNonEmptyString(d.directions) },
    { label: "all ingredient_name non-empty", ok: ings.length > 0 && ings.every((i) => isNonEmptyString(i.ingredient_name)) },
    { label: "all ingredient_category in enum", ok: ings.length > 0 && ings.every((i) => INGREDIENT_CATEGORIES.includes(i.ingredient_category)) },
    { label: "units in enum or null", ok: ings.every((i) => i.unit == null || UNITS.includes(i.unit)) },
  ];
  return fromChecks(checks);
}

// The faithfulness signal: did normalization keep EVERY source ingredient?
export function faithfulIngredients(output, context) {
  if (context?.vars?.expect_no_recipe === true) return res(true, 1, "n/a (no-recipe page)");
  const expected = Number(context?.vars?.expected_ingredient_count);
  const tol = Number(context?.vars?.ingredient_count_tolerance ?? 0);
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  const actual = Array.isArray(d.ingredients) ? d.ingredients.length : 0;
  if (!Number.isFinite(expected)) return res(true, 1, "no expected count set — skipped");
  const diff = Math.abs(actual - expected);
  const ok = diff <= tol;
  const score = expected > 0 ? Math.max(0, 1 - diff / expected) : (actual === 0 ? 1 : 0);
  return res(ok, score, `${actual} ingredients vs expected ${expected} (±${tol})`);
}

export function nameMatch(output, context) {
  if (context?.vars?.expect_no_recipe === true) return res(true, 1, "n/a (no-recipe page)");
  const expected = String(context?.vars?.expected_name || "").toLowerCase().trim();
  let d;
  try { d = extractJson(output); } catch (e) { return res(false, 0, `malformed JSON: ${e.message}`); }
  if (!expected) return res(true, 1, "no expected name set — skipped");
  const name = String(d.recipe_name || "").toLowerCase();
  const ok = name.includes(expected);
  return res(ok, ok ? 1 : 0, `recipe_name "${d.recipe_name}" ${ok ? "contains" : "MISSING"} "${expected}"`);
}
