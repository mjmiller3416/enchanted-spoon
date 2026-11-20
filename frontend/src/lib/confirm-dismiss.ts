/**
 * Open confirmation dialogs, newest last. The Android back handler and the
 * browser history guard dismiss the top one instead of leaving the page.
 */
const dismissers: Array<() => void> = [];

export function registerConfirmDismiss(dismiss: () => void): () => void {
  dismissers.push(dismiss);
  return () => {
    const index = dismissers.lastIndexOf(dismiss);
    if (index !== -1) dismissers.splice(index, 1);
  };
}

export function hasOpenConfirm(): boolean {
  return dismissers.length > 0;
}

/** Close the top confirmation without running its destructive action. */
export function dismissTopConfirm(): boolean {
  const dismiss = dismissers.at(-1);
  if (!dismiss) return false;
  dismiss();
  return true;
}
