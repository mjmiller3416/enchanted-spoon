// Genie chat prompt builder (ESM — package.json has "type":"module").
// Returns a chat message array: the REAL production system prompt
// (assistant-system.txt) + a mock "USER'S SAVED RECIPES" context block that
// production injects via get_full_system_prompt(user_context), then the
// conversation turns from vars.messages. promptfoo maps the `system` role to each
// provider's native system field. Tool-free by design — this measures the
// conversational output the user reads (voice/personality/helpfulness), not the
// Phase-4 tool-calling loop. See README "Genie chat eval".
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const RAW_SYSTEM = fs.readFileSync(path.join(here, "assistant-system.txt"), "utf8");

// Strip the "WHEN TO USE TOOLS" section for this TOOL-FREE conversational eval.
// With no tools bound, Gemini 3.x reads those instructions, attempts a function
// call, and returns EMPTY (finishReason MALFORMED_FUNCTION_CALL) — an artifact of
// the eval, not production (where the tools ARE declared). We measure the
// conversational voice, so replace that section with a direct-response instruction.
// GPT/Claude already answer inline regardless; this just levels the field.
const SYSTEM = RAW_SYSTEM.replace(
  /={10,}\nWHEN TO USE TOOLS\n={10,}[\s\S]*?(?=\n={10,}\nRECIPE GENERATION RULES)/,
  "Respond directly and conversationally in your own warm voice — give suggestions,\n" +
    "answers, and full recipes inline. (No tools/functions are available in this\n" +
    "context; never attempt to call one — just reply.)\n",
);

// Mock saved-recipes context so the prompt's "check her saved recipes first"
// behavior is observable (e.g. a chicken ask should surface the roast chicken).
const SAVED_RECIPES = `
===============================================================================
USER'S SAVED RECIPES
===============================================================================
- Lemon Herb Roast Chicken (chicken, dinner)
- Weeknight Beef Chili (beef, dinner)
- Creamy Tomato Basil Soup (vegetarian, lunch)
- Banana Oat Pancakes (breakfast)
- Garlic Butter Shrimp Pasta (seafood, dinner)
- Sheet-Pan Salmon & Asparagus (seafood, dinner)
`;

export default function ({ vars }) {
  const turns = Array.isArray(vars.messages) ? vars.messages : [];
  return [{ role: "system", content: SYSTEM + "\n" + SAVED_RECIPES }, ...turns];
}
