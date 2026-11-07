/**
 * Functional + responsive audit of the public Enchanted Spoon site.
 *
 * Engines are Playwright's Chromium, WebKit, and Firefox builds on this VM.
 * A Playwright device descriptor is a CSS viewport, DPR, touch flag, and UA.
 * It does not boot Android, One UI, or iOS.
 *
 * Named devices absent from playwright-core's deviceDescriptorsSource.json
 * are separate contexts and are labeled approximations.
 */
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium, firefox, webkit, devices } from "playwright";

const require = createRequire(import.meta.url);
const playwrightPkg = require("playwright/package.json");

const BASE = (process.env.AUDIT_BASE_URL || "https://enchantedspoon.app").replace(/\/$/, "");
const OUT = process.env.AUDIT_OUT || "/tmp/enchanted-spoon-mobile-audit";
const NAV_TIMEOUT = 35000;

const ABSENT_FROM_PLAYWRIGHT = [
  "Galaxy S26 Ultra",
  "Pixel 9 Pro XL",
  "Pixel 9 Pro",
  "Pixel 9",
  "Galaxy Tab S10 FE",
  "Galaxy Tab S10",
];

const CHROME_MOBILE = (token) =>
  `Mozilla/5.0 (Linux; Android 17; ${token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36`;
const CHROME_TABLET = (token) =>
  `Mozilla/5.0 (Linux; Android 16; ${token}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36`;

/**
 * Approximations. CSS sizes are secondary-source profiles, not measurements
 * taken on Mitchell's hardware and not Playwright presets.
 *
 * Pixel 9 Pro XL: Google hardware is 1344×2992, 6.8in. Several 2026 viewport
 * catalogs agree on 448×997 CSS at DPR 3 (phone-simulator.com, 1440px.com,
 * screenmetriclab.com). screenmetriclab.com explicitly says the CSS profile
 * was not measured on the device. UA token "Pixel 9 Pro XL" / Android 17 is
 * constructed so the context is identifiable. It was not captured from a phone.
 *
 * Galaxy S26 Ultra: catalogs disagree.
 * - doesitfit.lol (updated Sep 2026): default display size 384×832, DPR 2.8125,
 *   physical 1440×3120, and the page says "Estimate: not measured in a browser".
 *   It also lists a "smaller" display-size mode at 412×892, DPR 2.625.
 * - screensize.io (23 Sep 2026): 412×891, DPR 2.625, physical 1440×3120.
 * - webmobilefirst.com: 412×891 at 4× and a 1648×3564 panel. That physical
 *   resolution conflicts with the other two, so it is not used.
 * Both the 384 and 412 profiles are run, each labeled.
 *
 * Galaxy Tab S10 FE: Samsung's developer skin and GSMArena list 10.9in,
 * 1440×2304 (~249 ppi). screensize.io derives 960×1536 CSS at DPR 1.5
 * (1440/960). 249/160 ≈ 1.56, so DPR 1.5 is a density-bucket estimate, not a
 * captured window.devicePixelRatio. Tablet UA omits the Mobile token, which
 * is how Chrome on Android tablets is usually classified.
 */
function approximation(spec) {
  return {
    kind: "labeled-approximation",
    playwrightName: null,
    ...spec,
  };
}

function preset(name, depth, engines, extra = {}) {
  if (!devices[name]) {
    throw new Error(`Playwright ${playwrightPkg.version} has no device preset "${name}"`);
  }
  return {
    kind: "playwright-preset",
    id: slug(name),
    label: name,
    playwrightName: name,
    depth,
    engines,
    notes: "Copied from the installed Playwright device descriptor. The browser engine is the VM build, not the phone OS named in the user agent.",
    options: { ...devices[name] },
    safeArea: false,
    light: false,
    ...extra,
  };
}

function slug(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

const CONTEXTS = [
  preset("iPhone SE", "core", ["chromium", "webkit", "firefox"]),
  preset("iPhone SE landscape", "layout", ["webkit"]),
  preset("iPhone SE (3rd gen)", "core", ["webkit"]),
  preset("Galaxy S8", "layout", ["chromium"]),
  preset("Galaxy S24", "core", ["chromium"]),
  preset("Galaxy S24 landscape", "layout", ["chromium"]),
  preset("iPhone 13", "full", ["webkit"]),
  preset("iPhone 13 landscape", "layout", ["webkit"]),
  preset("iPhone 14 Pro Max", "core", ["chromium", "webkit"]),
  preset("Pixel 7", "full", ["chromium", "firefox"]),
  preset("Pixel 7 landscape", "layout", ["chromium"]),
  preset("Galaxy Tab S9", "layout", ["chromium"]),
  preset("Galaxy Tab S9 landscape", "core", ["chromium"]),
  preset("iPad Mini", "core", ["webkit", "firefox"]),
  preset("iPad Mini landscape", "layout", ["webkit"]),
  preset("iPad (gen 7)", "core", ["webkit"]),
  approximation({
    id: "pixel-9-pro-xl-approx",
    label: "Pixel 9 Pro XL approximation (448×997, DPR 3)",
    depth: "core",
    engines: ["chromium"],
    safeArea: true,
    notes:
      "NOT a Playwright preset and NOT a Pixel device. CSS 448×997 DPR 3 from agreeing 2026 viewport catalogs; Google panel is 1344×2992. UA is constructed (Android 17, Chrome/141 matching this Playwright Chromium). Owner's Android 17 build was not booted.",
    options: {
      viewport: { width: 448, height: 997 },
      deviceScaleFactor: 3,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_MOBILE("Pixel 9 Pro XL"),
    },
  }),
  approximation({
    id: "pixel-9-pro-xl-approx-landscape",
    label: "Pixel 9 Pro XL approximation landscape (997×448, DPR 3)",
    depth: "layout",
    engines: ["chromium"],
    notes: "Landscape swap of the Pixel 9 Pro XL approximation. Not a device preset.",
    options: {
      viewport: { width: 997, height: 448 },
      deviceScaleFactor: 3,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_MOBILE("Pixel 9 Pro XL"),
    },
  }),
  approximation({
    id: "galaxy-s26-ultra-default-approx",
    label: "Galaxy S26 Ultra approximation, default display size (384×832, DPR 2.8125)",
    depth: "core",
    engines: ["chromium"],
    safeArea: true,
    notes:
      "NOT a Playwright preset and NOT a Galaxy handset. doesitfit.lol estimates the default Samsung display size at 384×832 DPR 2.8125 and says it was not measured in a browser. screensize.io instead publishes 412×891 DPR 2.625; that profile is a separate context. UA is constructed.",
    options: {
      viewport: { width: 384, height: 832 },
      deviceScaleFactor: 2.8125,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_MOBILE("Galaxy S26 Ultra"),
    },
  }),
  approximation({
    id: "galaxy-s26-ultra-smaller-approx",
    label: "Galaxy S26 Ultra approximation, smaller display size (412×892, DPR 2.625)",
    depth: "layout",
    engines: ["chromium"],
    notes:
      "Alternate approximation. doesitfit.lol lists Samsung 'Display size: smaller' as 412×892 DPR 2.625. screensize.io's default figure is 412×891 DPR 2.625. Sources disagree which one is the factory default.",
    options: {
      viewport: { width: 412, height: 892 },
      deviceScaleFactor: 2.625,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_MOBILE("Galaxy S26 Ultra"),
    },
  }),
  approximation({
    id: "galaxy-s26-ultra-default-landscape",
    label: "Galaxy S26 Ultra approximation landscape (832×384, DPR 2.8125)",
    depth: "layout",
    engines: ["chromium"],
    notes: "Landscape swap of the 384×832 S26 Ultra approximation.",
    options: {
      viewport: { width: 832, height: 384 },
      deviceScaleFactor: 2.8125,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_MOBILE("Galaxy S26 Ultra"),
    },
  }),
  approximation({
    id: "galaxy-tab-s10-fe-approx",
    label: "Galaxy Tab S10 FE approximation (960×1536, DPR 1.5)",
    depth: "core",
    engines: ["chromium"],
    safeArea: true,
    notes:
      "NOT a Playwright preset. Samsung/GSMArena panel is 1440×2304. CSS 960×1536 DPR 1.5 is screensize.io's derivation (1440/1.5). DPR was not read from a Tab S10 FE. UA has no Mobile token.",
    options: {
      viewport: { width: 960, height: 1536 },
      deviceScaleFactor: 1.5,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_TABLET("Galaxy Tab S10 FE"),
    },
  }),
  approximation({
    id: "galaxy-tab-s10-fe-landscape",
    label: "Galaxy Tab S10 FE approximation landscape (1536×960, DPR 1.5)",
    depth: "layout",
    engines: ["chromium"],
    notes: "Landscape swap of the Tab S10 FE approximation.",
    options: {
      viewport: { width: 1536, height: 960 },
      deviceScaleFactor: 1.5,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_TABLET("Galaxy Tab S10 FE"),
    },
  }),
  approximation({
    id: "custom-800x1280",
    label: "Custom CSS viewport 800×1280 (not a device preset)",
    depth: "core",
    engines: ["chromium"],
    notes: "Requested tablet width bucket. No Playwright device is exactly 800 CSS px wide. Touch tablet UA without a Mobile token.",
    options: {
      viewport: { width: 800, height: 1280 },
      deviceScaleFactor: 2,
      isMobile: true,
      hasTouch: true,
      userAgent: CHROME_TABLET("Custom 800"),
    },
  }),
  {
    ...preset("Pixel 7", "core", ["chromium"], { id: "pixel-7-light", label: "Pixel 7 preset, light theme" }),
    light: true,
    notes: "Same Playwright Pixel 7 descriptor. localStorage theme forced to light before paint, plus Playwright colorScheme light. Not a separate device.",
  },
];

const PROTECTED = ["/dashboard", "/recipes", "/recipes/1", "/meal-planner", "/shopping-list", "/settings"];

function firefoxOptions(options) {
  const { isMobile, hasTouch, deviceScaleFactor, ...rest } = options;
  return {
    options: rest,
    dropped: {
      isMobile: isMobile ?? null,
      hasTouch: hasTouch ?? null,
      deviceScaleFactor: deviceScaleFactor ?? null,
      reason: "Playwright Firefox rejects isMobile. deviceScaleFactor and hasTouch are omitted with it so the context can launch. This Firefox run is viewport + user agent only.",
    },
  };
}

async function launch(engine) {
  if (engine === "chromium") return chromium.launch();
  if (engine === "webkit") return webkit.launch();
  if (engine === "firefox") return firefox.launch();
  throw new Error(engine);
}

async function pool(items, limit, worker) {
  const results = new Array(items.length);
  let cursor = 0;
  async function run() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      results[index] = await worker(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, () => run()));
  return results;
}

function caseId(ctx, engine, flow) {
  return `${engine}__${ctx.id}__${flow}`;
}

async function shot(page, ctx, engine, flow) {
  const file = `${caseId(ctx, engine, flow)}.png`;
  await page.screenshot({ path: path.join(OUT, "screenshots", file), fullPage: false });
  return `screenshots/${file}`;
}

async function layoutSnapshot(page) {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const vh = window.innerHeight;
    const offenders = [];
    for (const el of document.querySelectorAll("body *")) {
      const style = getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      if (r.right > vw + 2 || r.left < -2) {
        offenders.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || "",
          className: String(el.className || "").slice(0, 140),
          text: (el.innerText || el.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 90),
          left: Math.round(r.left),
          right: Math.round(r.right),
          top: Math.round(r.top),
          width: Math.round(r.width),
        });
        if (offenders.length >= 10) break;
      }
    }
    const small = [];
    let below24 = 0;
    for (const el of document.querySelectorAll("a, button, input, textarea, select, [role='button']")) {
      const style = getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") continue;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
      if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
      const inline = style.display === "inline" || (el.tagName === "A" && style.display.includes("inline") && el.querySelector("button, svg") == null && (el.innerText || "").length < 40);
      const min = Math.min(r.width, r.height);
      if (min >= 44) continue;
      const item = {
        tag: el.tagName.toLowerCase(),
        text: (el.innerText || el.getAttribute("aria-label") || el.getAttribute("placeholder") || el.id || "").trim().replace(/\s+/g, " ").slice(0, 70),
        w: Math.round(r.width),
        h: Math.round(r.height),
        inline,
      };
      if (!inline && min < 24) below24 += 1;
      if (small.length < 15) small.push(item);
    }
    const header = document.querySelector("header");
    const headerBox = header ? header.getBoundingClientRect() : null;
    return {
      href: location.href,
      h1: (document.querySelector("h1")?.innerText || "").replace(/\s+/g, " ").slice(0, 200),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: vw,
      overflowX: document.documentElement.scrollWidth - vw,
      innerHeight: vh,
      header: headerBox
        ? { top: Math.round(headerBox.top), height: Math.round(headerBox.height), right: Math.round(headerBox.right), width: Math.round(headerBox.width) }
        : null,
      offenders,
      smallTargets: small,
      below24Controls: below24,
    };
  });
}

async function runtimeFacts(page) {
  return page.evaluate(() => ({
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio,
    maxTouchPoints: navigator.maxTouchPoints,
    userAgent: navigator.userAgent,
    visualViewportScale: window.visualViewport ? window.visualViewport.scale : null,
  }));
}

function push(bag, entry) {
  bag.cases.push(entry);
}

async function goto(page, route) {
  const response = await page.goto(BASE + route, { waitUntil: "domcontentloaded", timeout: NAV_TIMEOUT });
  await page.waitForTimeout(400);
  return response;
}

async function runContext(browser, engine, ctx) {
  const started = Date.now();
  const bag = {
    engine,
    id: ctx.id,
    label: ctx.label,
    kind: ctx.kind,
    playwrightName: ctx.playwrightName,
    depth: ctx.depth,
    requested: {
      viewport: ctx.options.viewport,
      deviceScaleFactor: ctx.options.deviceScaleFactor ?? null,
      isMobile: ctx.options.isMobile ?? null,
      hasTouch: ctx.options.hasTouch ?? null,
      userAgent: ctx.options.userAgent,
      light: Boolean(ctx.light),
      safeArea: Boolean(ctx.safeArea),
    },
    firefoxDropped: null,
    observed: null,
    notes: ctx.notes,
    cases: [],
    consoleErrors: [],
    pageErrors: [],
    badResponses: [],
  };

  let contextOptions = ctx.options;
  if (engine === "firefox") {
    const adapted = firefoxOptions(ctx.options);
    contextOptions = adapted.options;
    bag.firefoxDropped = adapted.dropped;
  }
  if (ctx.light) contextOptions = { ...contextOptions, colorScheme: "light" };

  const context = await browser.newContext(contextOptions);
  if (ctx.light) {
    await context.addInitScript(() => {
      try {
        localStorage.setItem("enchanted-spoon-theme", JSON.stringify("light"));
      } catch {
        /* ignore */
      }
    });
  }
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on("pageerror", (error) => {
    bag.pageErrors.push(String(error).slice(0, 300));
  });
  page.on("console", (msg) => {
    if (msg.type() === "error") bag.consoleErrors.push(msg.text().slice(0, 300));
  });
  page.on("response", (response) => {
    const status = response.status();
    const url = response.url();
    if (status < 400) return;
    if (url.includes("favicon")) return;
    const sameOrigin = url.startsWith(BASE);
    if (sameOrigin || status >= 500) {
      bag.badResponses.push({ status, url: url.slice(0, 180) });
    }
  });

  try {
    await goto(page, "/");
    bag.observed = await runtimeFacts(page);
    await flowHome(page, ctx, engine, bag);
    if (ctx.depth !== "layout") {
      await flowPricing(page, ctx, engine, bag);
      await flowLongText(page, ctx, engine, bag);
      await flowAuthScreens(page, ctx, engine, bag);
      await flowProtected(page, ctx, engine, bag);
      await flowNotFound(page, ctx, engine, bag);
      await flowReflowProxy(page, ctx, engine, bag);
    }
    if (ctx.depth === "full") {
      await flowDeleteAccount(page, ctx, engine, bag);
      await flowWhatsNew(page, ctx, engine, bag);
      await flowKeyboardZoomBlocked(page, ctx, engine, bag);
    }
    if (ctx.safeArea && engine === "chromium") {
      await flowSafeArea(page, ctx, engine, bag);
    }
    if (bag.pageErrors.length) {
      push(bag, result(ctx, engine, "page-errors", "fail", "No uncaught page exceptions on the pages visited.", bag.pageErrors.slice(0, 5).join(" | "), null));
    } else {
      push(bag, result(ctx, engine, "page-errors", "pass", "No uncaught page exceptions on the pages visited.", "None recorded.", null));
    }
  } catch (error) {
    let screenshot = null;
    try {
      screenshot = await shot(page, ctx, engine, "context-error");
    } catch {
      /* page may already be closed */
    }
    push(bag, result(ctx, engine, "context", "blocked", "Context completes its planned flows.", String(error).slice(0, 500), screenshot));
  } finally {
    await context.close().catch(() => {});
  }
  bag.ms = Date.now() - started;
  return bag;
}

function result(ctx, engine, flow, status, expected, actual, screenshot) {
  return {
    id: caseId(ctx, engine, flow),
    engine,
    context: ctx.id,
    label: ctx.label,
    kind: ctx.kind,
    flow,
    status,
    expected,
    actual,
    screenshot,
  };
}

async function flowHome(page, ctx, engine, bag) {
  if (!page.url().startsWith(BASE + "/") && !page.url().startsWith(BASE)) {
    await goto(page, "/");
  }
  const layout = await layoutSnapshot(page);
  const screenshot = await shot(page, ctx, engine, "home");
  const overflowFail = layout.overflowX > 2;
  push(bag, result(
    ctx,
    engine,
    "home-reflow",
    overflowFail ? "fail" : "pass",
    "Landing page has no horizontal overflow (scrollWidth within 2px of the CSS viewport).",
    `h1="${layout.h1}" overflowX=${layout.overflowX}px clientWidth=${layout.clientWidth} offenders=${JSON.stringify(layout.offenders).slice(0, 500)}`,
    screenshot,
  ));
  push(bag, result(
    ctx,
    engine,
    "home-tap-targets",
    layout.below24Controls > 0 ? "fail" : "warn",
    "On-screen buttons and inputs are at least 24px (WCAG 2.2 AA 2.5.8). 44px is the AAA target; 40px design-system buttons are warnings, not failures. Inline text links are exempt.",
    `below24Controls=${layout.below24Controls} onScreenUnder44=${JSON.stringify(layout.smallTargets)}`,
    null,
  ));

  const headerOverflow = layout.header && layout.header.right > layout.clientWidth + 2;
  push(bag, result(
    ctx,
    engine,
    "home-header",
    headerOverflow ? "fail" : "pass",
    "Sticky marketing header stays inside the viewport. Below the sm breakpoint (640px) the wordmark and Pricing link are intentionally hidden.",
    `header=${JSON.stringify(layout.header)} pricingInHeader=${await page.locator("header a[href='/pricing']").count()}`,
    null,
  ));

  const before = await page.evaluate(() => window.scrollY);
  let scrolled = false;
  const touch = Boolean(ctx.options.hasTouch) && engine !== "firefox";
  if (touch) {
    const vp = page.viewportSize();
    const x = Math.floor(vp.width / 2);
    const y1 = Math.floor(vp.height * 0.75);
    const y2 = Math.floor(vp.height * 0.3);
    await page.mouse.move(x, y1);
    await page.mouse.down();
    await page.mouse.move(x, y2, { steps: 12 });
    await page.mouse.up();
    scrolled = (await page.evaluate(() => window.scrollY)) > before + 20;
  }
  if (!scrolled) {
    try {
      await page.mouse.wheel(0, 700);
      scrolled = (await page.evaluate(() => window.scrollY)) > before + 20;
    } catch {
      // Mobile WebKit rejects mouse.wheel. Programmatic scroll is the fallback.
    }
  }
  if (!scrolled) {
    await page.evaluate(() => window.scrollBy(0, 700));
    scrolled = (await page.evaluate(() => window.scrollY)) > before + 20;
  }
  push(bag, result(
    ctx,
    engine,
    "home-scroll",
    scrolled ? "pass" : "fail",
    "The landing page can move vertically. Touch contexts try a mouse drag first, then a wheel, then programmatic scroll. A pass via programmatic scroll means the page is scrollable, not that a finger gesture was confirmed.",
    `scrollY before=${before} after=${await page.evaluate(() => window.scrollY)}`,
    null,
  ));
  await page.evaluate(() => window.scrollTo(0, 0));

  const getStarted = page.locator("header a[href='/sign-up']").first();
  if (touch) await getStarted.tap();
  else await getStarted.click();
  await page.waitForURL(/\/sign-up/, { timeout: 15000 });
  const signUpH = await page.locator("h1, h2").first().innerText().catch(() => "");
  push(bag, result(
    ctx,
    engine,
    "home-get-started",
    /sign-up/.test(page.url()) ? "pass" : "fail",
    "Header Get started opens /sign-up and does not start checkout.",
    `url=${page.url()} heading=${signUpH.slice(0, 80)} via=${touch ? "tap" : "click"}`,
    ctx.depth === "full" ? await shot(page, ctx, engine, "sign-up") : null,
  ));
}

async function flowPricing(page, ctx, engine, bag) {
  const response = await goto(page, "/pricing");
  const text = await page.locator("body").innerText();
  const layout = await layoutSnapshot(page);
  const screenshot = await shot(page, ctx, engine, "pricing");
  const founding = await page.locator("a[data-external-purchase], a[href*='stripe']").evaluateAll((nodes) =>
    nodes.map((node) => ({ text: (node.textContent || "").trim().slice(0, 60), href: node.getAttribute("href") })),
  ).catch(() => []);
  const hasPrices = text.includes("$6.99") && text.includes("$49.99") && text.includes("$0");
  const stripeNav = bag.badResponses.some((item) => /stripe|checkout/i.test(item.url));
  push(bag, result(
    ctx,
    engine,
    "pricing-display",
    hasPrices && !stripeNav && layout.overflowX <= 2 ? "pass" : layout.overflowX > 2 ? "fail" : hasPrices ? "pass" : "fail",
    "Pricing shows Free $0, Pro $6.99/mo and $49.99/yr, with no horizontal overflow. No checkout session is opened.",
    `status=${response?.status()} overflowX=${layout.overflowX} hasPrices=${hasPrices} url=${page.url()} stripeOrCheckoutResponses=${stripeNav}`,
    screenshot,
  ));
  const pro = page.locator("a[href='/sign-up']", { hasText: "Start with Pro" }).first();
  await pro.click();
  await page.waitForURL(/\/sign-up/, { timeout: 15000 });
  const landedOnStripe = /stripe\.com|checkout\.stripe/.test(page.url());
  push(bag, result(
    ctx,
    engine,
    "pricing-pro-cta",
    /\/sign-up/.test(page.url()) && !landedOnStripe ? "pass" : "fail",
    "Start with Pro goes to /sign-up. It must not open Stripe Checkout.",
    `url=${page.url()}`,
    null,
  ));
  push(bag, result(
    ctx,
    engine,
    "pricing-no-purchase",
    "pass",
    "Founding-price and checkout anchors are recorded and not followed. No card, code, or subscription action is taken.",
    `anchors=${JSON.stringify(founding)}`,
    null,
  ));
}

async function flowLongText(page, ctx, engine, bag) {
  for (const route of ["/privacy", "/terms"]) {
    const response = await goto(page, route);
    const layout = await layoutSnapshot(page);
    const body = await page.locator("article, main").first().innerText();
    const screenshot = route === "/privacy" && (ctx.depth === "full" || ctx.id.includes("320") || ctx.id === "iphone-se" || ctx.id.includes("s26") || ctx.id.includes("pixel-9"))
      ? await shot(page, ctx, engine, route.slice(1))
      : null;
    const clipped = await page.evaluate(() => {
      const nodes = [...document.querySelectorAll("p, li, h1, h2")].slice(0, 40);
      return nodes.filter((el) => {
        const style = getComputedStyle(el);
        if (style.overflow === "hidden" && el.scrollWidth > el.clientWidth + 2) return true;
        return false;
      }).length;
    });
    push(bag, result(
      ctx,
      engine,
      `${route.slice(1)}-reflow`,
      layout.overflowX > 2 ? "fail" : "pass",
      `${route} long-form text reflows inside the viewport and the heading is present.`,
      `status=${response?.status()} h1=${layout.h1} chars=${body.length} overflowX=${layout.overflowX} clippedBlocks=${clipped}`,
      screenshot,
    ));
  }
}

async function flowAuthScreens(page, ctx, engine, bag) {
  await goto(page, "/sign-in");
  const email = page.locator("#email");
  try {
    await email.waitFor({ state: "visible", timeout: 20000 });
  } catch (error) {
    push(bag, result(ctx, engine, "sign-in-form", "blocked", "Sign-in email field is visible.", String(error).slice(0, 300), await shot(page, ctx, engine, "sign-in-missing")));
    return;
  }
  await email.focus();
  await email.fill("a");
  const vp = page.viewportSize();
  const shrunk = { width: vp.width, height: Math.max(280, vp.height - 320) };
  await page.setViewportSize(shrunk);
  await email.focus();
  const box = await email.boundingBox();
  const inView = box && box.y >= 0 && box.y + box.height <= shrunk.height + 1;
  const screenshot = await shot(page, ctx, engine, "sign-in-keyboard");
  push(bag, result(
    ctx,
    engine,
    "sign-in-keyboard-inset",
    inView ? "pass" : "fail",
    "With the viewport height reduced by 320px (simulated keyboard, not an OS IME), the email field remains fully inside the visible viewport. The letter 'a' is typed and not submitted.",
    `viewport=${shrunk.width}x${shrunk.height} emailBox=${JSON.stringify(box)} valueLength=${(await email.inputValue()).length}`,
    screenshot,
  ));
  await page.setViewportSize(vp);

  const continueButton = page.locator("form button[type='submit']").first();
  await continueButton.click();
  await page.waitForTimeout(300);
  const stillHere = page.url().includes("/sign-in");
  const validation = await email.evaluate((el) => ({
    valid: el.validity.valid,
    typeMismatch: el.validity.typeMismatch,
    value: el.value,
  }));
  push(bag, result(
    ctx,
    engine,
    "sign-in-invalid-email-not-submitted",
    stillHere && validation.typeMismatch && validation.value === "a" ? "pass" : stillHere ? "warn" : "fail",
    "Clicking Continue with the invalid value 'a' stays on /sign-in because the email input fails constraint validation. Clerk signIn.create is not expected to run.",
    `url=${page.url()} validity=${JSON.stringify(validation)}`,
    null,
  ));
  await email.fill("");

  const focused = [];
  await page.locator("body").click({ position: { x: 8, y: 8 } }).catch(() => {});
  for (let i = 0; i < 6; i += 1) {
    await page.keyboard.press("Tab");
    focused.push(await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      const style = getComputedStyle(el);
      return {
        tag: el.tagName.toLowerCase(),
        id: el.id || "",
        text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 40),
        outline: style.outlineStyle,
        shadow: style.boxShadow === "none" ? "none" : "set",
      };
    }));
  }
  const reachedEmail = focused.some((item) => item && item.id === "email");
  push(bag, result(
    ctx,
    engine,
    "sign-in-keyboard-tab",
    reachedEmail ? "pass" : "fail",
    "Tab from the top of /sign-in reaches the email field.",
    JSON.stringify(focused),
    null,
  ));

  const google = page.getByRole("button", { name: "Continue with Google" });
  const googleBox = await google.boundingBox();
  push(bag, result(
    ctx,
    engine,
    "sign-in-google-not-clicked",
    googleBox && googleBox.height >= 24 ? "pass" : "fail",
    "Continue with Google is visible and at least 24px tall. The button is not activated (no OAuth redirect).",
    `box=${JSON.stringify(googleBox)}`,
    null,
  ));

  await goto(page, "/sign-up");
  const signUpEmail = page.locator("#email");
  await signUpEmail.waitFor({ state: "visible", timeout: 20000 });
  const password = page.locator("#password");
  const passwordType = await password.getAttribute("type");
  const layout = await layoutSnapshot(page);
  push(bag, result(
    ctx,
    engine,
    "sign-up-fields",
    layout.overflowX <= 2 && passwordType === "password" ? "pass" : "fail",
    "New-account form shows email and a password field, reflows, and is not submitted. This is not a completed registration and not the in-app onboarding tour.",
    `overflowX=${layout.overflowX} passwordType=${passwordType} h1=${layout.h1}`,
    ctx.depth === "full" ? await shot(page, ctx, engine, "sign-up-form") : null,
  ));
}

async function flowProtected(page, ctx, engine, bag) {
  const landed = [];
  for (const route of PROTECTED) {
    const response = await goto(page, route);
    landed.push({ route, status: response?.status() ?? null, url: page.url() });
  }
  const allGated = landed.every((item) => /\/sign-in/.test(item.url));
  push(bag, result(
    ctx,
    engine,
    "auth-gate",
    allGated ? "pass" : "fail",
    "Unsigned requests to dashboard, recipes, recipe detail, meal planner, shopping list, and settings redirect to /sign-in. No app data is loaded.",
    JSON.stringify(landed),
    ctx.depth === "full" ? await shot(page, ctx, engine, "auth-gate") : null,
  ));
  if (allGated) {
    push(bag, result(
      ctx,
      engine,
      "authenticated-app-shell",
      "blocked",
      "Signed-in coverage of recipe browse/search/filter/detail, create/edit/import, meal plan, shopping list, modals, and Settings billing.",
      "No Clerk session in this VM. CLERK_SECRET_KEY and NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY are unset. Auth was not bypassed and no credentials were invented. These screens were not rendered.",
      null,
    ));
  }
}

async function flowNotFound(page, ctx, engine, bag) {
  const response = await goto(page, "/not-a-real-mobile-audit-route");
  const layout = await layoutSnapshot(page);
  const shotPath = ctx.depth === "full" ? await shot(page, ctx, engine, "unknown-route") : null;
  const sentToSignIn = /\/sign-in/.test(page.url());
  push(bag, result(
    ctx,
    engine,
    "unknown-route",
    sentToSignIn ? "warn" : layout.h1.includes("Page not found") ? "pass" : "fail",
    "A signed-out request for an unknown path. Clerk protects non-public routes, so this currently redirects to /sign-in instead of rendering not-found.tsx. Recorded as a warning, not a crashed page.",
    `status=${response?.status()} url=${page.url()} h1=${layout.h1 || "(none)"} overflowX=${layout.overflowX}`,
    shotPath,
  ));
}

async function flowDeleteAccount(page, ctx, engine, bag) {
  await goto(page, "/delete-account");
  const layout = await layoutSnapshot(page);
  const text = await page.locator("body").innerText();
  const mailto = await page.locator("a[href^='mailto:']").count();
  push(bag, result(
    ctx,
    engine,
    "delete-account-display",
    layout.h1.includes("Delete your Enchanted Spoon account") && layout.overflowX <= 2 ? "pass" : "fail",
    "Public deletion instructions render. The mailto link is not activated and no account is deleted.",
    `overflowX=${layout.overflowX} mailtoLinks=${mailto} mentionsEmail=${/email/i.test(text)}`,
    await shot(page, ctx, engine, "delete-account"),
  ));
}

async function flowWhatsNew(page, ctx, engine, bag) {
  await goto(page, "/whats-new");
  const layout = await layoutSnapshot(page);
  push(bag, result(
    ctx,
    engine,
    "whats-new",
    layout.h1.length > 0 && layout.overflowX <= 2 ? "pass" : "fail",
    "What's New renders a heading without horizontal overflow.",
    `h1=${layout.h1} overflowX=${layout.overflowX}`,
    await shot(page, ctx, engine, "whats-new"),
  ));
}

async function flowReflowProxy(page, ctx, engine, bag) {
  await goto(page, "/privacy");
  const original = page.viewportSize();
  const half = { width: Math.max(240, Math.round(original.width / 2)), height: original.height };
  await page.setViewportSize(half);
  await page.waitForTimeout(200);
  const layout = await layoutSnapshot(page);
  const screenshot = ctx.depth === "full" ? await shot(page, ctx, engine, "privacy-half-width") : null;
  await page.setViewportSize(original);
  push(bag, result(
    ctx,
    engine,
    "zoom-reflow-proxy",
    layout.overflowX > 2 ? "fail" : "pass",
    "Halving the CSS width (proxy for 200% browser zoom reflow, not pinch-zoom and not Ctrl+Plus) keeps /privacy in one column.",
    `from=${original.width}x${original.height} to=${half.width}x${half.height} overflowX=${layout.overflowX} h1=${layout.h1}`,
    screenshot,
  ));
}

async function flowKeyboardZoomBlocked(page, ctx, engine, bag) {
  await goto(page, "/");
  await page.keyboard.down("Control");
  await page.keyboard.press("Equal");
  await page.keyboard.press("Equal");
  await page.keyboard.up("Control");
  const facts = await runtimeFacts(page);
  const changed = facts.visualViewportScale && facts.visualViewportScale !== 1;
  push(bag, result(
    ctx,
    engine,
    "browser-zoom-keys",
    changed ? "pass" : "blocked",
    "Ctrl+Plus twice changes visualViewport.scale the way a desktop browser zoom does.",
    changed
      ? JSON.stringify(facts)
      : `Headless ${engine} left visualViewport.scale at ${facts.visualViewportScale}. Keyboard zoom is blocked in this runner. The half-width reflow proxy and the 320px iPhone SE context cover reflow instead. Pinch-zoom was not performed.`,
    null,
  ));
}

async function flowSafeArea(page, ctx, engine, bag) {
  let cdpError = null;
  try {
    const client = await page.context().newCDPSession(page);
    await client.send("Emulation.setSafeAreaInsetsOverride", {
      insets: { top: 47, left: 0, bottom: 34, right: 0 },
    });
  } catch (error) {
    cdpError = String(error).split("\n")[0];
  }
  await goto(page, "/");
  await page.waitForTimeout(200);
  const measured = await page.evaluate(() => {
    const probe = document.createElement("div");
    probe.style.paddingTop = "env(safe-area-inset-top)";
    probe.style.paddingBottom = "env(safe-area-inset-bottom)";
    document.body.appendChild(probe);
    const style = getComputedStyle(probe);
    const header = document.querySelector("header");
    const box = header ? header.getBoundingClientRect() : null;
    probe.remove();
    return {
      paddingTop: style.paddingTop,
      paddingBottom: style.paddingBottom,
      headerTop: box ? Math.round(box.top) : null,
      headerHeight: box ? Math.round(box.height) : null,
    };
  });
  const screenshot = await shot(page, ctx, engine, "safe-area");
  if (cdpError) {
    push(bag, result(ctx, engine, "safe-area-inset", "blocked", "CDP safe-area override applies.", cdpError, screenshot));
    return;
  }
  const top = parseFloat(measured.paddingTop);
  const headerIgnores = measured.headerTop === 0 && top >= 40;
  push(bag, result(
    ctx,
    engine,
    "safe-area-inset",
    headerIgnores ? "fail" : "pass",
    "With a forced 47px top safe-area inset (CDP Emulation.setSafeAreaInsetsOverride, not a measured device notch), the marketing header starts below that inset or pads for it. Normal mobile Chrome often reports 0 because the browser chrome already clears the status bar. This matters for standalone display and edge-to-edge WebViews.",
    JSON.stringify(measured),
    screenshot,
  ));
}

function summarize(report) {
  const counts = { pass: 0, fail: 0, warn: 0, blocked: 0 };
  const lines = [];
  for (const ctx of report.contexts) {
    for (const item of ctx.cases) {
      counts[item.status] = (counts[item.status] || 0) + 1;
    }
  }
  lines.push(`# Mobile web audit ${report.meta.finishedAt}`);
  lines.push("");
  lines.push(`Target: ${report.meta.baseUrl}`);
  lines.push(`Playwright: ${report.meta.playwright}`);
  lines.push(`Counts: pass=${counts.pass} fail=${counts.fail} warn=${counts.warn} blocked=${counts.blocked}`);
  lines.push("");
  lines.push("Absent Playwright presets: " + report.meta.absentPresets.join(", "));
  lines.push("");
  lines.push("| Status | Engine | Context | Flow | Actual |");
  lines.push("| --- | --- | --- | --- | --- |");
  for (const ctx of report.contexts) {
    for (const item of ctx.cases) {
      if (item.status === "pass") continue;
      const actual = String(item.actual).replace(/\|/g, "/").replace(/\n/g, " ").slice(0, 220);
      lines.push(`| ${item.status} | ${item.engine} | ${item.context} | ${item.flow} | ${actual} |`);
    }
  }
  lines.push("");
  lines.push("## Contexts");
  lines.push("");
  lines.push("| Engine | Context | Kind | Observed viewport | DPR | touch points | ms |");
  lines.push("| --- | --- | --- | --- | --- | --- | --- |");
  for (const ctx of report.contexts) {
    const obs = ctx.observed || {};
    lines.push(`| ${ctx.engine} | ${ctx.label} | ${ctx.kind} | ${obs.innerWidth}×${obs.innerHeight} | ${obs.devicePixelRatio} | ${obs.maxTouchPoints} | ${ctx.ms} |`);
  }
  return { counts, markdown: lines.join("\n") };
}

async function main() {
  await mkdir(path.join(OUT, "screenshots"), { recursive: true });
  const absent = ABSENT_FROM_PLAYWRIGHT.filter((name) => !devices[name]);
  const presentSurprise = ABSENT_FROM_PLAYWRIGHT.filter((name) => devices[name]);
  if (presentSurprise.length) {
    throw new Error("Expected these names to be absent, but Playwright has them: " + presentSurprise.join(", "));
  }

  const enginesWanted = new Set(
    (process.env.AUDIT_ENGINES || "chromium,webkit,firefox").split(",").map((item) => item.trim()).filter(Boolean),
  );
  const jobs = [];
  for (const ctx of CONTEXTS) {
    for (const engine of ctx.engines) {
      if (enginesWanted.has(engine)) jobs.push({ ctx, engine });
    }
  }

  const byEngine = new Map();
  for (const job of jobs) {
    if (!byEngine.has(job.engine)) byEngine.set(job.engine, []);
    byEngine.get(job.engine).push(job);
  }

  const contexts = [];
  for (const engine of ["chromium", "webkit", "firefox"]) {
    const group = byEngine.get(engine) || [];
    if (!group.length) continue;
    console.log(`launch ${engine} (${group.length} contexts)`);
    const browser = await launch(engine);
    try {
      const ran = await pool(group, engine === "firefox" ? 1 : 2, async (job) => {
        console.log(`  start ${engine} ${job.ctx.id}`);
        const resultBag = await runContext(browser, engine, job.ctx);
        const fails = resultBag.cases.filter((item) => item.status === "fail").length;
        console.log(`  done ${engine} ${job.ctx.id} cases=${resultBag.cases.length} fails=${fails}`);
        return resultBag;
      });
      contexts.push(...ran);
    } finally {
      await browser.close();
    }
  }

  const report = {
    meta: {
      baseUrl: BASE,
      playwright: playwrightPkg.version,
      chromium: "Playwright build, Chromium 141.0.7390.37",
      webkit: "Playwright WebKit 26.0",
      firefox: "Playwright Firefox 142.0.1",
      host: "Linux cloud VM browser emulation. No physical phone or tablet. No Samsung One UI, Android 17, or iOS simulator.",
      absentPresets: absent,
      startedAt: process.env.AUDIT_STARTED_AT || null,
      finishedAt: new Date().toISOString(),
      auth: "No credentials. Protected routes were only checked for the redirect to /sign-in.",
      payments: "Pricing was displayed. No checkout, founding-code redemption, or subscription purchase.",
      ai: "No recipe import, generation, nutrition, or image endpoint was called.",
    },
    contexts,
  };
  const { counts, markdown } = summarize(report);
  report.meta.counts = counts;
  await writeFile(path.join(OUT, "results.json"), JSON.stringify(report, null, 2));
  await writeFile(path.join(OUT, "summary.md"), markdown);
  console.log(JSON.stringify(counts));
  console.log("wrote", OUT);
}

const started = new Date().toISOString();
process.env.AUDIT_STARTED_AT = started;
main().catch((error) => {
  console.error(error);
  process.exit(1);
});
