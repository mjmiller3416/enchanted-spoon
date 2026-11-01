import { describe, expect, it } from "vitest";
import { isFoundingOfferOpen, planSunsetInstant, zonedLocalToUtc } from "@/lib/plan-sunset";

describe("plan sunset", () => {
  const sunset = zonedLocalToUtc("2027-03-31T23:59:00", "America/New_York");

  it("is 11:59 PM Eastern, which is 03:59 UTC the next day", () => {
    expect(sunset.toISOString()).toBe("2027-04-01T03:59:00.000Z");
    expect(planSunsetInstant("2027-03-31T23:59:00", "America/New_York").toISOString()).toBe(
      sunset.toISOString(),
    );
  });

  it("keeps FOUNDER30 and free access open through that instant, including earlier UTC", () => {
    expect(isFoundingOfferOpen(sunset, sunset)).toBe(true);
    expect(isFoundingOfferOpen(new Date("2027-04-01T00:00:00.000Z"), sunset)).toBe(true);
    expect(isFoundingOfferOpen(new Date("2027-03-31T23:59:00.000Z"), sunset)).toBe(true);
  });

  it("closes one second later in Eastern time", () => {
    expect(isFoundingOfferOpen(new Date("2027-04-01T03:59:01.000Z"), sunset)).toBe(false);
  });
});