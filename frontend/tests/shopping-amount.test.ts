import { describe, expect, it } from "vitest";
import { unitRequiresQuantity } from "@/lib/formValidation";
import { formatShoppingAmount } from "@/lib/utils";

describe("shopping amount display", () => {
  it("shows a convertible total in its unit", () => {
    expect(formatShoppingAmount(1.5, "lb")).toBe("1 ½ lb");
    expect(formatShoppingAmount(0.75, "cup")).toBe("¾ cup");
    expect(formatShoppingAmount(3, "clove")).toBe("3 clove");
  });

  it("does not turn a missing amount or to-taste into 0", () => {
    expect(formatShoppingAmount(0, "")).toBe("");
    expect(formatShoppingAmount(0, null)).toBe("");
    expect(formatShoppingAmount(0, "to taste")).toBe("to taste");
    expect(formatShoppingAmount(2, "to-taste")).toBe("to taste");
    expect(formatShoppingAmount(2, null)).toBe("2");
  });
});

describe("unit quantity requirements", () => {
  it("requires a quantity for mass and volume spellings", () => {
    expect(unitRequiresQuantity("lb")).toBe(true);
    expect(unitRequiresQuantity("lbs")).toBe(true);
    expect(unitRequiresQuantity("pound(s)")).toBe(true);
    expect(unitRequiresQuantity("tbsp")).toBe(true);
    expect(unitRequiresQuantity("T")).toBe(true);
    expect(unitRequiresQuantity("t")).toBe(true);
    expect(unitRequiresQuantity("fl. oz.")).toBe(true);
    expect(unitRequiresQuantity("g")).toBe(true);
  });

  it("leaves counts and unknown units optional", () => {
    expect(unitRequiresQuantity("")).toBe(false);
    expect(unitRequiresQuantity("whole")).toBe(false);
    expect(unitRequiresQuantity("clove")).toBe(false);
    expect(unitRequiresQuantity("can")).toBe(false);
    expect(unitRequiresQuantity("pinch")).toBe(false);
    expect(unitRequiresQuantity("to-taste")).toBe(false);
  });
});
