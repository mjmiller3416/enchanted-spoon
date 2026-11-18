import { describe, expect, it, vi, afterEach } from "vitest";
import { ApiError } from "@/lib/api/base";
import {
  MAX_PHOTO_EDGE_PX,
  MAX_PHOTO_INPUT_BYTES,
  looksLikeHeic,
  mapOrientedPoint,
  orientedDraw,
  stripJpegExif,
  photoImportErrorMessage,
  photoImportMessages,
  photoRejectionReason,
  postPhotoImport,
  readJpegOrientation,
} from "@/lib/photo-import";

const BANNED = /\b(ai|gpt|gemini|artificial intelligence)\b/i;

function jpegWithOrientation(orientation: number): { bytes: Uint8Array; file: File } {
  const tiff = new Uint8Array(26);
  const view = new DataView(tiff.buffer);
  view.setUint8(0, 0x49);
  view.setUint8(1, 0x49);
  view.setUint16(2, 42, true);
  view.setUint32(4, 8, true);
  view.setUint16(8, 1, true);
  view.setUint16(10, 0x0112, true);
  view.setUint16(12, 3, true);
  view.setUint32(14, 1, true);
  view.setUint16(18, orientation, true);
  const payload = new Uint8Array(6 + tiff.length);
  payload.set([0x45, 0x78, 0x69, 0x66, 0x00, 0x00], 0);
  payload.set(tiff, 6);
  const segmentLength = payload.length + 2;
  const bytes = new Uint8Array(8 + payload.length);
  bytes[0] = 0xff;
  bytes[1] = 0xd8;
  bytes[2] = 0xff;
  bytes[3] = 0xe1;
  bytes[4] = (segmentLength >> 8) & 0xff;
  bytes[5] = segmentLength & 0xff;
  bytes.set(payload, 6);
  bytes[6 + payload.length] = 0xff;
  bytes[7 + payload.length] = 0xd9;
  return { bytes, file: new File([bytes], "sideways.jpg", { type: "image/jpeg" }) };
}

function heicBytes(): File {
  const box = new Uint8Array([
    0x00, 0x00, 0x00, 0x18,
    0x66, 0x74, 0x79, 0x70,
    0x68, 0x65, 0x69, 0x63,
    0x00, 0x00, 0x00, 0x00,
  ]);
  return new File([box], "IMG_0001.JPG", { type: "image/jpeg" });
}

describe("photo import copy", () => {
  it("never uses banned words", () => {
    for (const message of Object.values(photoImportMessages)) {
      expect(message).not.toMatch(BANNED);
    }
  });
});

describe("photo file checks", () => {
  it("reads a JPEG orientation tag and can strip it", async () => {
    const tagged = jpegWithOrientation(6);
    await expect(readJpegOrientation(tagged.file)).resolves.toBe(6);
    await expect(readJpegOrientation(jpegWithOrientation(1).file)).resolves.toBe(1);
    const plain = stripJpegExif(tagged.bytes);
    const copy = new ArrayBuffer(plain.byteLength);
    new Uint8Array(copy).set(plain);
    const stripped = new File([copy], "plain.jpg", { type: "image/jpeg" });
    await expect(readJpegOrientation(stripped)).resolves.toBe(1);
    expect(Array.from(plain.subarray(0, 2))).toEqual([0xff, 0xd8]);
  });

  it("turns a portrait EXIF tag into a tall canvas", () => {
    const draw = orientedDraw(6, 40, 20, MAX_PHOTO_EDGE_PX);
    expect(draw.canvasWidth).toBe(20);
    expect(draw.canvasHeight).toBe(40);
    expect(mapOrientedPoint(draw, 0, 0)).toEqual({ x: 20, y: 0 });
  });

  it("scales the long edge down to 1600px", () => {
    const draw = orientedDraw(1, 3200, 1600, MAX_PHOTO_EDGE_PX);
    expect(draw.canvasWidth).toBe(1600);
    expect(draw.canvasHeight).toBe(800);
    expect(mapOrientedPoint(draw, 3200, 1600)).toEqual({ x: 1600, y: 800 });
  });

  it("names HEIC even when the file is labeled JPEG", async () => {
    expect(await looksLikeHeic(heicBytes())).toBe(true);
    expect(await photoRejectionReason(heicBytes())).toBe(photoImportMessages.heic);
    expect(await photoRejectionReason(new File([], "empty.jpg", { type: "image/jpeg" }))).toBe(photoImportMessages.empty);
    expect(await photoRejectionReason(new File(["hello"], "notes.txt", { type: "text/plain" }))).toBe(photoImportMessages.unsupported);
  });

  it("rejects a file too large to open", async () => {
    const huge = new File([new Uint8Array(MAX_PHOTO_INPUT_BYTES + 1)], "huge.jpg", { type: "image/jpeg" });
    expect(await photoRejectionReason(huge)).toBe(photoImportMessages.tooLarge);
  });
});

describe("photo import errors", () => {
  it("keeps a specific server message and strips banned words", () => {
    const missing = new ApiError("No recipe was found in that photo.", 422);
    expect(photoImportErrorMessage(missing)).toBe("No recipe was found in that photo.");
    const leaked = new ApiError("AI features are not available on this plan.", 403, {
      detail: { error: "expired" },
    });
    expect(photoImportErrorMessage(leaked)).toBe(photoImportMessages.generic);
    expect(photoImportErrorMessage(leaked)).not.toMatch(BANNED);
  });

  it("maps quota, timeout, offline, and cancel", () => {
    const quota = new ApiError("Monthly limit reached", 429, {
      detail: { error: "usage_limit_exceeded", field: "recipes_imported", current: 5, limit: 5 },
    });
    expect(photoImportErrorMessage(quota)).toBe(photoImportMessages.quota);
    const trial = new ApiError("Start your 7-day trial", 403, { detail: { error: "trial_required" } });
    expect(photoImportErrorMessage(trial)).toBe(photoImportMessages.trial);
    expect(photoImportErrorMessage(new ApiError("slow", 408))).toBe(photoImportMessages.timeout);
    expect(photoImportErrorMessage(new TypeError("Failed to fetch"))).toBe(photoImportMessages.offline);
    expect(photoImportErrorMessage(new DOMException("canceled", "AbortError"))).toBeNull();
  });
});

describe("photo import request", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the photos as multipart without a JSON content type", async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const headers = init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBeUndefined();
      const body = init.body as FormData;
      expect(body.getAll("images")).toHaveLength(1);
      expect(body.get("allowed_categories")).toBe("italian,other");
      return new Response(JSON.stringify({ success: true, recipe: { recipe_name: "Card" } }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File([new Uint8Array([1, 2, 3])], "card.jpg", { type: "image/jpeg" });
    const result = await postPhotoImport([file], ["italian", "other"], null);
    expect(result.recipe?.recipe_name).toBe("Card");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/ai/recipe-import/photo");
  });

  it("turns a hung request into a timeout and a cancel into no error", async () => {
    vi.stubGlobal("fetch", vi.fn((_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      });
    })));
    const file = new File([new Uint8Array([1])], "card.jpg", { type: "image/jpeg" });
    await expect(postPhotoImport([file], [], null, undefined, 20)).rejects.toMatchObject({ status: 408 });

    const controller = new AbortController();
    const pending = postPhotoImport([file], [], null, controller.signal, 5_000);
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    try {
      await pending;
    } catch (error) {
      expect(photoImportErrorMessage(error)).toBeNull();
    }
  });
});
