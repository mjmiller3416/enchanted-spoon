/** Legacy unscoped personal data has no provable owner; never assign it to
 * whichever account signs in next. Server settings remain the migration source. */
export function accountStorageKey(key: string, userId: string | null | undefined): string {
  return `${key}:${userId ?? "guest"}`;
}
