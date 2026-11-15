import { describe, expect, it } from "vitest";
import { describeConnections } from "@/app/(app)/settings/_components/ConnectedAppsCard";

const at = "2026-11-15T00:00:00Z";

describe("Connected Apps wording", () => {
  it("says what each kind of connection can do", () => {
    expect(describeConnections([{ client_name: "ChatGPT", connected_at: at, scope: "mcp" }])).toBe(
      "ChatGPT can see and change your recipes, meal plan and shopping list."
    );
    expect(describeConnections([{ client_name: "Amazon Alexa", connected_at: at, scope: "alexa" }])).toBe(
      "Amazon Alexa can add to and read your shopping list."
    );
    expect(
      describeConnections([
        { client_name: "ChatGPT", connected_at: at },
        { client_name: "ChatGPT", connected_at: at, scope: "mcp" },
        { client_name: "Amazon Alexa", connected_at: at, scope: "alexa" },
      ])
    ).toBe(
      "ChatGPT can see and change your recipes, meal plan and shopping list. Amazon Alexa can add to and read your shopping list."
    );
  });
});
