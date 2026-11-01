import { beforeEach, describe, expect, it } from "vitest";
import {
  applyShoppingQueue,
  cacheShoppingList,
  enqueueShoppingWrite,
  readShoppingListForDisplay,
} from "@/lib/offline-shopping";
import type { ShoppingListResponseDTO } from "@/types/shopping";

const list = {
  items: [
    { id: 1, have: false, flagged: false },
    { id: 2, have: false, flagged: false },
  ],
  checked_items: 0,
  total_items: 2,
} as ShoppingListResponseDTO;

describe("offline shopping cache", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("keeps a check-off on the cached list until it syncs", () => {
    cacheShoppingList(list);
    enqueueShoppingWrite({ id: 1, field: "have", value: true });
    const shown = readShoppingListForDisplay();
    expect(shown?.items.find((item) => item.id === 1)?.have).toBe(true);
    expect(shown?.checked_items).toBe(1);
    expect(applyShoppingQueue(list).items[1]?.have).toBe(false);
  });
});
