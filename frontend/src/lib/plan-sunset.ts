/**
 * Shared end of grandfathered free access and the FOUNDER30 offer.
 * Default is March 31, 2027 at 11:59 PM America/New_York.
 * Keep in sync with backend FREE_PLAN_SUNSET_AT / FREE_PLAN_SUNSET_TIMEZONE.
 */

const DEFAULT_SUNSET_LOCAL = "2027-03-31T23:59:00";
const DEFAULT_SUNSET_TIME_ZONE = "America/New_York";

export function planSunsetTimeZone(): string {
  return process.env.NEXT_PUBLIC_FREE_PLAN_SUNSET_TIMEZONE || DEFAULT_SUNSET_TIME_ZONE;
}

export function planSunsetLocal(): string {
  return process.env.NEXT_PUBLIC_FREE_PLAN_SUNSET_AT || DEFAULT_SUNSET_LOCAL;
}

/**
 * UTC instant for a civil time in an IANA zone.
 * `localIso` is `YYYY-MM-DDTHH:mm:ss` without an offset.
 */
export function zonedLocalToUtc(localIso: string, timeZone: string): Date {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/.exec(localIso);
  if (!match) {
    throw new Error(`Invalid plan sunset: ${localIso}`);
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const second = Number(match[6] ?? "0");
  const desiredUtc = Date.UTC(year, month - 1, day, hour, minute, second);
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const parts = Object.fromEntries(
    formatter.formatToParts(new Date(desiredUtc)).map((part) => [part.type, part.value]),
  );
  const zonedAsUtc = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour),
    Number(parts.minute),
    Number(parts.second),
  );
  return new Date(desiredUtc - (zonedAsUtc - desiredUtc));
}

export function planSunsetInstant(
  localIso: string = planSunsetLocal(),
  timeZone: string = planSunsetTimeZone(),
): Date {
  return zonedLocalToUtc(localIso, timeZone);
}

export function isFoundingOfferOpen(now: Date, sunset: Date = planSunsetInstant()): boolean {
  return now.getTime() <= sunset.getTime();
}
