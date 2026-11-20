import { dismissTopConfirm, hasOpenConfirm } from "@/lib/confirm-dismiss";

/**
 * What the Android hardware back button should do.
 *
 * Registering a Capacitor `backButton` listener replaces the WebView's
 * default `goBack()`. `history-back` is that default. `ignore` matches the
 * plugin when the WebView cannot go back (it consumes the press and does
 * not exit). `dismiss-dialog` closes a confirmation and does not navigate.
 */
export type NativeBackAction = "dismiss-dialog" | "history-back" | "ignore";

export function decideNativeBackAction(input: {
  confirmOpen: boolean;
  canGoBack: boolean;
}): NativeBackAction {
  if (input.confirmOpen) return "dismiss-dialog";
  if (input.canGoBack) return "history-back";
  return "ignore";
}

export function handleNativeBackButton(event: { canGoBack: boolean }): NativeBackAction {
  const action = decideNativeBackAction({
    confirmOpen: hasOpenConfirm(),
    canGoBack: event.canGoBack,
  });
  if (action === "dismiss-dialog") dismissTopConfirm();
  else if (action === "history-back") window.history.back();
  return action;
}
