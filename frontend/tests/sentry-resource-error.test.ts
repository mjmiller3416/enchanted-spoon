import { describe, expect, it } from "vitest"
import { sentryOptions } from "@/lib/sentry"
import { describeResourceErrorRejection } from "@/lib/sentry-resource-error"

const SCRIPT_URL = "https://clerk.enchantedspoon.app/npm/@clerk/clerk-js@5/dist/clerk.browser.js"
const IMAGE_URL = "https://res.cloudinary.com/demo/image/upload/sample.jpg"
const LINK_URL = "https://enchantedspoon.app/_next/static/css/app.css"

function eventLike(target: unknown) {
  return { type: "error", target }
}

describe("describeResourceErrorRejection", () => {
  it("returns null for Error and string reasons", () => {
    expect(describeResourceErrorRejection(new Error("boom"))).toBeNull()
    expect(describeResourceErrorRejection("Event `Event` (type=error) captured as promise rejection")).toBeNull()
    expect(describeResourceErrorRejection(null)).toBeNull()
    expect(describeResourceErrorRejection(undefined)).toBeNull()
    expect(describeResourceErrorRejection(404)).toBeNull()
  })

  it("leaves chunk-load Errors alone even when they carry type error", () => {
    const chunk = new Error("Loading chunk 12 failed.\n(error: https://enchantedspoon.app/_next/static/chunks/a.js)")
    ;(chunk as Error & { type?: string }).type = "error"
    expect(describeResourceErrorRejection(chunk)).toBeNull()
  })

  it("names a script, img, or link from src or href", () => {
    expect(describeResourceErrorRejection(eventLike({ tagName: "SCRIPT", src: SCRIPT_URL }))).toEqual({
      ignore: false,
      message: `Failed to load script ${SCRIPT_URL}`,
      extras: { tagName: "SCRIPT", src: SCRIPT_URL, href: null },
    })

    expect(describeResourceErrorRejection(eventLike({ tagName: "IMG", src: IMAGE_URL, href: "" }))).toEqual({
      ignore: false,
      message: `Failed to load img ${IMAGE_URL}`,
      extras: { tagName: "IMG", src: IMAGE_URL, href: null },
    })

    expect(describeResourceErrorRejection(eventLike({ tagName: "LINK", href: LINK_URL }))).toEqual({
      ignore: false,
      message: `Failed to load link ${LINK_URL}`,
      extras: { tagName: "LINK", src: null, href: LINK_URL },
    })
  })

  it("prefers src when an element has both src and href", () => {
    expect(
      describeResourceErrorRejection(
        eventLike({ tagName: "SCRIPT", src: SCRIPT_URL, href: "https://enchantedspoon.app/fallback" })
      )
    ).toMatchObject({
      ignore: false,
      message: `Failed to load script ${SCRIPT_URL}`,
    })
  })

  it("ignores browser extension URLs", () => {
    const urls = [
      "chrome-extension://abc/content.js",
      "moz-extension://abc/content.js",
      "safari-web-extension://abc/content.js",
      "safari-extension://abc/content.js",
      "Chrome-Extension://abc/content.js",
    ]
    for (const url of urls) {
      expect(describeResourceErrorRejection(eventLike({ tagName: "SCRIPT", src: url }))).toEqual({ ignore: true })
    }
    expect(
      describeResourceErrorRejection(
        eventLike({ tagName: "LINK", href: "moz-extension://abc/style.css", src: SCRIPT_URL })
      )
    ).toEqual({ ignore: true })
  })

  it("keeps ordinary URLs that merely mention an extension scheme", () => {
    const src = "https://example.com/app.js?next=chrome-extension://abc/content.js"
    expect(describeResourceErrorRejection(eventLike({ tagName: "SCRIPT", src }))).toMatchObject({
      ignore: false,
      message: `Failed to load script ${src}`,
    })
  })

  it("keeps a missing target or url without throwing", () => {
    expect(describeResourceErrorRejection({ type: "error" })).toEqual({
      ignore: false,
      message: "Failed to load resource (unknown)",
      extras: { tagName: null, src: null, href: null },
    })
    expect(describeResourceErrorRejection({ type: "error", target: null })).toEqual({
      ignore: false,
      message: "Failed to load resource (unknown)",
      extras: { tagName: null, src: null, href: null },
    })
    expect(describeResourceErrorRejection(eventLike({ tagName: "SCRIPT" }))).toEqual({
      ignore: false,
      message: "Failed to load resource (unknown)",
      extras: { tagName: "SCRIPT", src: null, href: null },
    })

    const throwing = {
      type: "error",
      get target(): unknown {
        throw new Error("blocked")
      },
    }
    expect(describeResourceErrorRejection(throwing)).toEqual({
      ignore: false,
      message: "Failed to load resource (unknown)",
      extras: { tagName: null, src: null, href: null },
    })
  })

  it("ignores events that are not error events", () => {
    expect(describeResourceErrorRejection({ type: "load", target: { tagName: "IMG", src: IMAGE_URL } })).toBeNull()
  })
})

describe("sentryOptions.beforeSend", () => {
  const beforeSend = sentryOptions.beforeSend
  if (!beforeSend) throw new Error("expected beforeSend")

  function resourceEvent() {
    return {
      type: undefined,
      message: "Event `Event` (type=error) captured as promise rejection",
      exception: {
        values: [
          {
            type: "Event",
            value: "Event `Event` (type=error) captured as promise rejection",
          },
        ],
      },
      extra: { keep: "yes" },
    }
  }

  it("names the failed resource and keeps other extra data", () => {
    const event = resourceEvent()
    const result = beforeSend(event, {
      originalException: eventLike({ tagName: "SCRIPT", src: SCRIPT_URL }),
    })

    expect(result).toBe(event)
    expect(result?.message).toBe(`Failed to load script ${SCRIPT_URL}`)
    expect(result?.exception?.values?.[0]).toMatchObject({
      type: "ResourceLoadError",
      value: `Failed to load script ${SCRIPT_URL}`,
    })
    expect(result?.extra).toEqual({
      keep: "yes",
      tagName: "SCRIPT",
      src: SCRIPT_URL,
      href: null,
    })
  })

  it("drops extension resource errors without mutating the event", () => {
    const event = resourceEvent()
    const result = beforeSend(event, {
      originalException: eventLike({ tagName: "SCRIPT", src: "chrome-extension://abc/content.js" }),
    })
    expect(result).toBeNull()
    expect(event.message).toBe("Event `Event` (type=error) captured as promise rejection")
    expect(event.extra).toEqual({ keep: "yes" })
  })

  it("leaves ordinary errors unchanged", () => {
    const event = {
      type: undefined,
      message: "Something else broke",
      exception: { values: [{ type: "TypeError", value: "Something else broke" }] },
      extra: { keep: "yes" },
    }
    const before = {
      message: event.message,
      exception: { values: [{ type: "TypeError", value: "Something else broke" }] },
      extra: { keep: "yes" },
    }
    const result = beforeSend(event, { originalException: new Error("Something else broke") })
    expect(result).toBe(event)
    expect(event.message).toBe(before.message)
    expect(event.exception).toEqual(before.exception)
    expect(event.extra).toEqual(before.extra)
  })

  it("does not treat the generic captured-as-promise-rejection string as an event", () => {
    const event = resourceEvent()
    const result = beforeSend(event, {
      originalException: "Event `Event` (type=error) captured as promise rejection",
    })
    expect(result).toBe(event)
    expect(event.exception.values[0].value).toBe("Event `Event` (type=error) captured as promise rejection")
  })

  it("still names the resource when the event has no exception values yet", () => {
    const event = { type: undefined, extra: {} }
    const result = beforeSend(event, {
      originalException: { type: "error", target: null },
    })
    expect(result?.message).toBe("Failed to load resource (unknown)")
    expect(result?.exception?.values).toEqual([
      { type: "ResourceLoadError", value: "Failed to load resource (unknown)" },
    ])
  })
})
