"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { useCurrentUser } from "@/hooks/api";

/**
 * Tags error reports with the signed-in user's internal id — the same
 * "user #<id>" that feedback issues cite. Never the email.
 */
export function ErrorReportingUser() {
  const { data: user } = useCurrentUser();

  useEffect(() => {
    Sentry.setUser(user ? { id: String(user.id) } : null);
  }, [user]);

  return null;
}
