import type { ShoppingListResponseDTO } from "@/types/shopping";

const LIST_KEY = "enchanted-spoon-shopping-cache";
const QUEUE_KEY = "enchanted-spoon-shopping-queue";

export interface QueuedShoppingWrite {
  id: number;
  field: "have" | "flagged";
  value: boolean;
}

function readJson<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

export function cacheShoppingList(list: ShoppingListResponseDTO): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(LIST_KEY, JSON.stringify(list));
}

export function readCachedShoppingList(): ShoppingListResponseDTO | null {
  return readJson<ShoppingListResponseDTO>(LIST_KEY);
}

export function readShoppingQueue(): QueuedShoppingWrite[] {
  return readJson<QueuedShoppingWrite[]>(QUEUE_KEY) ?? [];
}

export function enqueueShoppingWrite(entry: QueuedShoppingWrite): void {
  const queue = readShoppingQueue().filter(
    (item) => !(item.id === entry.id && item.field === entry.field),
  );
  queue.push(entry);
  window.localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export function replaceShoppingQueue(queue: QueuedShoppingWrite[]): void {
  window.localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

/** Apply queued check-offs onto a cached list so the offline screen matches the taps. */
export function applyShoppingQueue(list: ShoppingListResponseDTO): ShoppingListResponseDTO {
  const queue = readShoppingQueue();
  if (queue.length === 0) return list;
  const items = list.items.map((item) => {
    const updates = queue.filter((entry) => entry.id === item.id);
    if (updates.length === 0) return item;
    return updates.reduce((current, entry) => ({ ...current, [entry.field]: entry.value }), item);
  });
  return {
    ...list,
    items,
    checked_items: items.filter((item) => item.have).length,
  };
}

export function readShoppingListForDisplay(): ShoppingListResponseDTO | null {
  const cached = readCachedShoppingList();
  return cached ? applyShoppingQueue(cached) : null;
}
