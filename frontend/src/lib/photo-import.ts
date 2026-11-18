/**
 * Client-side preparation for "Import from photo".
 *
 * Photos are oriented, scaled, and re-encoded in the browser before upload.
 * The source file never leaves the device; the request sends the JPEG only.
 */

import { ApiError, API_BASE, toApiError } from "@/lib/api/base";
import { nativeClientHeaders } from "@/lib/native/platform";
import type { RecipeImportResponseDTO } from "@/types/ai";

export const MAX_PHOTO_COUNT = 4;
export const MAX_PHOTO_EDGE_PX = 1600;
/** Files larger than this are not decoded in the browser. */
export const MAX_PHOTO_INPUT_BYTES = 15 * 1024 * 1024;
export const MAX_PHOTO_OUTPUT_BYTES = 1_500_000;
export const PHOTO_IMPORT_TIMEOUT_MS = 60_000;

const ACCEPTED_TYPES = new Set(["image/jpeg", "image/jpg", "image/png", "image/webp"]);
const HEIC_BRANDS = new Set(["heic", "heix", "hevc", "hevx", "heim", "heis", "heif", "mif1", "msf1"]);
const JPEG_QUALITIES = [0.85, 0.7, 0.55];
const BANNED_COPY = /\b(ai|gpt|gemini|artificial intelligence)\b/i;

export const photoImportMessages = {
  heic: "This photo is HEIC, which this import can't read. Save it as JPEG, or take a new photo, then try again.",
  unsupported: "Use a JPEG, PNG, or WebP photo.",
  empty: "That photo is empty. Choose a different one.",
  tooLarge: "That photo is too large. Choose one under 10 MB, or take a new photo.",
  tooLargeAfter: "That photo is still too large after compressing it. Try a smaller picture.",
  unreadable: "We couldn't read that photo. Use a JPEG, PNG, or WebP.",
  limit: "You can import up to 4 photos at a time.",
  timeout: "Reading the recipe took too long. Try again, or use a closer photo.",
  offline: "We couldn't reach the server. Check your connection and try again.",
  noRecipe: "No recipe was found in that photo. Try a clearer picture of the card or page.",
  quota: "You've used your recipe imports for now. Your photos are still here.",
  trial: "Start your 7-day trial to import a recipe from a photo. Your photos are still here.",
  readOnly: "This account is view-only, so recipes can't be imported. Your photos are still here.",
  unavailable: "Import from photo isn't available right now.",
  generic: "We couldn't read those photos. Please try again.",
} as const;

export function isPhotoImportEnabled(): boolean {
  return process.env.NEXT_PUBLIC_PHOTO_IMPORT_ENABLED === "true";
}

export class PhotoImportClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PhotoImportClientError";
  }
}

export interface OrientedDraw {
  canvasWidth: number;
  canvasHeight: number;
  a: number;
  b: number;
  c: number;
  d: number;
  e: number;
  f: number;
}

/** Canvas transform that bakes EXIF orientation into pixels, then scales. */
export function orientedDraw(
  orientation: number,
  sourceWidth: number,
  sourceHeight: number,
  maxEdge: number,
): OrientedDraw {
  const swaps = orientation >= 5 && orientation <= 8;
  const orientedWidth = swaps ? sourceHeight : sourceWidth;
  const orientedHeight = swaps ? sourceWidth : sourceHeight;
  const longEdge = Math.max(orientedWidth, orientedHeight, 1);
  const scale = Math.min(1, maxEdge / longEdge);
  const canvasWidth = Math.max(1, Math.round(orientedWidth * scale));
  const canvasHeight = Math.max(1, Math.round(orientedHeight * scale));
  const s = scale;
  switch (orientation) {
    case 2:
      return { canvasWidth, canvasHeight, a: -s, b: 0, c: 0, d: s, e: canvasWidth, f: 0 };
    case 3:
      return { canvasWidth, canvasHeight, a: -s, b: 0, c: 0, d: -s, e: canvasWidth, f: canvasHeight };
    case 4:
      return { canvasWidth, canvasHeight, a: s, b: 0, c: 0, d: -s, e: 0, f: canvasHeight };
    case 5:
      return { canvasWidth, canvasHeight, a: 0, b: s, c: s, d: 0, e: 0, f: 0 };
    case 6:
      return { canvasWidth, canvasHeight, a: 0, b: s, c: -s, d: 0, e: canvasWidth, f: 0 };
    case 7:
      return { canvasWidth, canvasHeight, a: 0, b: -s, c: -s, d: 0, e: canvasWidth, f: canvasHeight };
    case 8:
      return { canvasWidth, canvasHeight, a: 0, b: -s, c: s, d: 0, e: 0, f: canvasHeight };
    default:
      return { canvasWidth, canvasHeight, a: s, b: 0, c: 0, d: s, e: 0, f: 0 };
  }
}

export function mapOrientedPoint(draw: OrientedDraw, x: number, y: number): { x: number; y: number } {
  return {
    x: draw.a * x + draw.c * y + draw.e,
    y: draw.b * x + draw.d * y + draw.f,
  };
}

function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  const copy = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(copy).set(bytes);
  return copy;
}

function readBlob(blob: Blob): Promise<Uint8Array> {
  if (typeof blob.arrayBuffer === "function") {
    return blob.arrayBuffer().then((buffer) => new Uint8Array(buffer));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new Uint8Array(reader.result as ArrayBuffer));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read the photo"));
    reader.readAsArrayBuffer(blob);
  });
}

async function readPrefix(file: Blob, length: number): Promise<Uint8Array> {
  return readBlob(file.size > length ? file.slice(0, length) : file);
}

/** Drop the EXIF segment so the decoder cannot rotate the pixels a second time. */
export function stripJpegExif(bytes: Uint8Array): Uint8Array {
  if (bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return bytes;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const parts: Uint8Array[] = [bytes.subarray(0, 2)];
  let offset = 2;
  while (offset + 4 < bytes.length) {
    if (bytes[offset] !== 0xff) {
      parts.push(bytes.subarray(offset));
      break;
    }
    const marker = bytes[offset + 1];
    if (marker === 0xda || marker === 0xd9) {
      parts.push(bytes.subarray(offset));
      break;
    }
    const size = view.getUint16(offset + 2);
    const next = offset + 2 + size;
    if (size < 2 || next > bytes.length) {
      parts.push(bytes.subarray(offset));
      break;
    }
    const isExif = marker === 0xe1 && bytes[offset + 4] === 0x45 && bytes[offset + 5] === 0x78;
    if (!isExif) parts.push(bytes.subarray(offset, next));
    offset = next;
  }
  const stripped = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0));
  let cursor = 0;
  for (const part of parts) {
    stripped.set(part, cursor);
    cursor += part.length;
  }
  return stripped;
}

function readUint16(view: DataView, offset: number, little: boolean): number {
  return view.getUint16(offset, little);
}

function readUint32(view: DataView, offset: number, little: boolean): number {
  return view.getUint32(offset, little);
}

/** EXIF orientation (1–8), or 1 when the file has no tag. JPEG only. */
export async function readJpegOrientation(file: Blob): Promise<number> {
  const bytes = await readPrefix(file, 128 * 1024);
  if (bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return 1;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let offset = 2;
  while (offset + 4 < bytes.length) {
    if (bytes[offset] !== 0xff) break;
    const marker = bytes[offset + 1];
    if (marker === 0xda || marker === 0xd9) break;
    const size = view.getUint16(offset + 2);
    if (size < 2 || offset + 2 + size > bytes.length) break;
    if (marker === 0xe1) {
      return orientationFromExif(bytes.subarray(offset + 4, offset + 2 + size));
    }
    offset += 2 + size;
  }
  return 1;
}

function orientationFromExif(segment: Uint8Array): number {
  if (segment.length < 14) return 1;
  const header = String.fromCharCode(...segment.subarray(0, 6));
  if (header !== "Exif\0\0") return 1;
  const view = new DataView(segment.buffer, segment.byteOffset, segment.byteLength);
  const little = segment[6] === 0x49;
  if (readUint16(view, 8, little) !== 42) return 1;
  const ifd = readUint32(view, 10, little) + 6;
  if (ifd + 2 > segment.length) return 1;
  const count = readUint16(view, ifd, little);
  for (let index = 0; index < count; index += 1) {
    const entry = ifd + 2 + index * 12;
    if (entry + 12 > segment.length) break;
    if (readUint16(view, entry, little) !== 0x0112) continue;
    const value = readUint16(view, entry + 8, little);
    return value >= 1 && value <= 8 ? value : 1;
  }
  return 1;
}

export async function looksLikeHeic(file: File): Promise<boolean> {
  const type = file.type.toLowerCase();
  const name = file.name.toLowerCase();
  if (type === "image/heic" || type === "image/heif" || name.endsWith(".heic") || name.endsWith(".heif")) {
    return true;
  }
  const bytes = await readPrefix(file, 64);
  const windowText = String.fromCharCode(...bytes);
  const index = windowText.indexOf("ftyp");
  if (index < 0 || index + 8 > windowText.length) return false;
  return HEIC_BRANDS.has(windowText.slice(index + 4, index + 8));
}

function isAcceptedPhotoType(file: File): boolean {
  const type = file.type.toLowerCase();
  if (ACCEPTED_TYPES.has(type)) return true;
  if (type && type !== "application/octet-stream") return false;
  return /\.(jpe?g|png|webp)$/i.test(file.name);
}

/** A message when this file should not be decoded, or null when it can. */
export async function photoRejectionReason(file: File): Promise<string | null> {
  if (file.size === 0) return photoImportMessages.empty;
  if (await looksLikeHeic(file)) return photoImportMessages.heic;
  if (file.size > MAX_PHOTO_INPUT_BYTES) return photoImportMessages.tooLarge;
  if (!isAcceptedPhotoType(file)) return photoImportMessages.unsupported;
  return null;
}

export interface PreparedRecipePhoto {
  file: File;
  width: number;
  height: number;
}

function canvasOf(width: number, height: number): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function encodeJpeg(canvas: HTMLCanvasElement, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", quality);
  });
}

async function decodePhoto(file: File): Promise<{ bitmap: ImageBitmap; orientation: number }> {
  if (typeof createImageBitmap !== "function") {
    throw new PhotoImportClientError(photoImportMessages.unreadable);
  }
  const orientation = await readJpegOrientation(file);
  // Browsers apply the EXIF tag while decoding and ignore imageOrientation
  // "none". Strip the tag first so the transform below runs once.
  let source: Blob = file;
  if (orientation !== 1) {
    const stripped = stripJpegExif(await readBlob(file));
    source = new Blob([toArrayBuffer(stripped)], { type: "image/jpeg" });
  }
  try {
    const bitmap = await createImageBitmap(source);
    return { bitmap, orientation };
  } catch {
    throw new PhotoImportClientError(photoImportMessages.unreadable);
  }
}

/**
 * Orient, scale the long edge to 1600px, and encode a JPEG under 1.5 MB.
 * Throws PhotoImportClientError with copy safe to show in the wizard.
 */
export async function prepareRecipePhoto(file: File): Promise<PreparedRecipePhoto> {
  const reason = await photoRejectionReason(file);
  if (reason) throw new PhotoImportClientError(reason);

  const { bitmap, orientation } = await decodePhoto(file);
  try {
    if (bitmap.width < 1 || bitmap.height < 1) {
      throw new PhotoImportClientError(photoImportMessages.unreadable);
    }
    const draw = orientedDraw(orientation, bitmap.width, bitmap.height, MAX_PHOTO_EDGE_PX);
    const canvas = canvasOf(draw.canvasWidth, draw.canvasHeight);
    const context = canvas.getContext("2d");
    if (!context) throw new PhotoImportClientError(photoImportMessages.unreadable);
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, draw.canvasWidth, draw.canvasHeight);
    context.setTransform(draw.a, draw.b, draw.c, draw.d, draw.e, draw.f);
    context.drawImage(bitmap, 0, 0);
    context.setTransform(1, 0, 0, 1, 0, 0);

    let encoded: Blob | null = null;
    for (const quality of JPEG_QUALITIES) {
      encoded = await encodeJpeg(canvas, quality);
      if (encoded && encoded.size <= MAX_PHOTO_OUTPUT_BYTES) break;
    }
    if (!encoded) throw new PhotoImportClientError(photoImportMessages.unreadable);
    if (encoded.size > MAX_PHOTO_OUTPUT_BYTES) {
      throw new PhotoImportClientError(photoImportMessages.tooLargeAfter);
    }
    const base = file.name.replace(/\.[^.]+$/, "") || "recipe-photo";
    return {
      file: new File([encoded], `${base}.jpg`, { type: "image/jpeg" }),
      width: draw.canvasWidth,
      height: draw.canvasHeight,
    };
  } finally {
    bitmap.close?.();
  }
}

function isAbort(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === "AbortError") ||
    (error instanceof Error && error.name === "AbortError")
  );
}

function gateCode(error: ApiError): string | null {
  const detail = error.details?.detail;
  if (!detail || typeof detail !== "object" || Array.isArray(detail)) return null;
  const code = (detail as { error?: unknown }).error;
  return typeof code === "string" ? code : null;
}

function cleanCopy(message: string, fallback: string): string {
  const trimmed = message.trim();
  if (!trimmed || BANNED_COPY.test(trimmed)) return fallback;
  return trimmed;
}

/**
 * Wizard copy for a failed import. Null means the person canceled it,
 * so the photos stay and no error is shown.
 */
export function photoImportErrorMessage(error: unknown): string | null {
  if (isAbort(error)) return null;
  if (error instanceof PhotoImportClientError) {
    return cleanCopy(error.message, photoImportMessages.generic);
  }
  if (error instanceof ApiError) {
    if (error.status === 408) return photoImportMessages.timeout;
    if (error.status === 413) return photoImportMessages.tooLarge;
    if (error.status === 422) return cleanCopy(error.message, photoImportMessages.noRecipe);
    if (error.status === 400) return cleanCopy(error.message, photoImportMessages.unsupported);
    if (error.status === 404) return photoImportMessages.unavailable;
    if (error.status === 429) return photoImportMessages.quota;
    if (error.status === 403) {
      const code = gateCode(error);
      if (code === "trial_required") return photoImportMessages.trial;
      if (code === "read_only" || code === "account_read_only") return photoImportMessages.readOnly;
      return photoImportMessages.generic;
    }
    if (error.status >= 500) return photoImportMessages.generic;
    return cleanCopy(error.message, photoImportMessages.generic);
  }
  if (error instanceof TypeError) return photoImportMessages.offline;
  return photoImportMessages.generic;
}

export async function postPhotoImport(
  files: File[],
  allowedCategories: string[],
  token?: string | null,
  signal?: AbortSignal,
  timeoutMs: number = PHOTO_IMPORT_TIMEOUT_MS,
): Promise<RecipeImportResponseDTO> {
  const body = new FormData();
  for (const file of files) {
    body.append("images", file, file.name || "recipe-photo.jpg");
  }
  if (allowedCategories.length > 0) {
    body.append("allowed_categories", allowedCategories.join(","));
  }

  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), timeoutMs);
  const combined = signal ? AbortSignal.any([signal, timeout.signal]) : timeout.signal;
  const headers: Record<string, string> = { ...nativeClientHeaders() };
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const response = await fetch(`${API_BASE}/api/ai/recipe-import/photo`, {
      method: "POST",
      body,
      headers,
      signal: combined,
    });
    if (!response.ok) {
      throw await toApiError(response, photoImportMessages.generic);
    }
    return (await response.json()) as RecipeImportResponseDTO;
  } catch (error) {
    if (signal?.aborted) {
      throw new DOMException("The import was canceled.", "AbortError");
    }
    if (timeout.signal.aborted) {
      throw new ApiError(photoImportMessages.timeout, 408);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
