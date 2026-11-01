import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api/base";
import { classifyAiGateError } from "@/lib/paywall";

describe("trial_required is the error code, not HTTP 403", () => {
  it("opens trial checkout when the code is trial_required on a non-403 status", () => {
    const error = new ApiError("Start your 7-day trial", 400, {
      detail: { error: "trial_required", message: "Start your 7-day trial" },
    });
    expect(classifyAiGateError(error)).toEqual({
      reason: "trial_required",
      featureLabel: "AI features",
    });
  });

  it("does not treat every 403 as a trial", () => {
    const readOnly = new ApiError("read only", 403, {
      detail: { error: "read_only", message: "This account is read-only." },
    });
    expect(classifyAiGateError(readOnly)?.reason).toBe("read_only");

    const prose = new ApiError("Pro subscription required for this feature", 403, {
      detail: "Pro subscription required for this feature",
    });
    expect(classifyAiGateError(prose)?.reason).toBe("pro_required");
  });
});
