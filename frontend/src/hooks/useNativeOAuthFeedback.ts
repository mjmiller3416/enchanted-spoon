"use client";

import { useEffect, useRef } from "react";

import { NATIVE_AUTH_EVENT, type NativeAuthDetail } from "@/lib/native/native-oauth";

interface NativeOAuthFeedback {
  setError: (message: string) => void;
  setIsLoading: (loading: boolean) => void;
  setOauthPending: (pending: null) => void;
}

/**
 * The native OAuth attempt outlives the button click: the system browser
 * returns through `appUrlOpen`. Surface that result on the form that started
 * it, and stop the spinner if the browser is closed first.
 */
export function useNativeOAuthFeedback(feedback: NativeOAuthFeedback): void {
  const feedbackRef = useRef(feedback);
  feedbackRef.current = feedback;

  useEffect(() => {
    const onResult = (event: Event) => {
      const detail = (event as CustomEvent<NativeAuthDetail>).detail;
      if (!detail) return;
      event.preventDefault();
      const current = feedbackRef.current;
      current.setIsLoading(false);
      current.setOauthPending(null);
      if (detail.status === "error") current.setError(detail.message);
    };
    window.addEventListener(NATIVE_AUTH_EVENT, onResult);
    return () => window.removeEventListener(NATIVE_AUTH_EVENT, onResult);
  }, []);
}
