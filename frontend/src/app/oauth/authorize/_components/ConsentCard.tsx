"use client";

import { useEffect, useMemo, useState } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { useSearchParams } from "next/navigation";
import { AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Logo } from "@/components/layout/Logo";
import { oauthApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { getErrorMessage } from "@/lib/utils";
import type { AuthorizeCheckDTO, AuthorizeParams } from "@/types/oauth";

const PARAM_NAMES: (keyof AuthorizeParams)[] = [
  "response_type",
  "client_id",
  "redirect_uri",
  "code_challenge",
  "code_challenge_method",
  "state",
  "scope",
  "resource",
];

/** Leave for the app that asked (its redirect URI). Stable, so effects don't re-run. */
const goTo = (url: string) => window.location.assign(url);

/**
 * ConsentCard — "ChatGPT wants to use Enchanted Spoon as you" with Allow and
 * Cancel. Validates the request with the backend first: a request that can't
 * be trusted to redirect shows an error here; a malformed but safe one goes
 * straight back to the app that asked. Allow and Cancel are sent with the
 * signed-in person's Clerk token and answered with where to go next.
 */
export function ConsentCard({
  navigate = goTo,
}: {
  /** Where the browser goes next (replaceable in tests). */
  navigate?: (url: string) => void;
}) {
  const searchParams = useSearchParams();
  const { getToken } = useAuth();
  const { user } = useUser();
  const [check, setCheck] = useState<AuthorizeCheckDTO | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<"allow" | "deny" | null>(null);

  const params = useMemo(() => {
    const out = {} as AuthorizeParams;
    for (const name of PARAM_NAMES) out[name] = searchParams.get(name);
    return out;
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    oauthApi
      .check(params)
      .then((result) => {
        if (cancelled) return;
        if (result.status === "redirect" && result.redirect_to) {
          navigate(result.redirect_to);
          return;
        }
        setCheck(result);
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err, "This request couldn't be checked. Try again."));
      });
    return () => {
      cancelled = true;
    };
  }, [params, navigate]);

  const decide = async (decision: "allow" | "deny") => {
    setPending(decision);
    setError("");
    try {
      const token = await getToken();
      const result = await oauthApi.decide(params, decision, token);
      navigate(result.redirect_to);
    } catch (err) {
      setError(getErrorMessage(err, "That didn't work. Try again."));
      setPending(null);
    }
  };

  const appName = check?.client_name || "An app";
  const account = user?.primaryEmailAddress?.emailAddress;
  const failed = check?.status === "error" ? check.message : null;

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="items-center text-center">
        <Logo className="mx-auto h-12 w-auto" />
        <CardTitle className="text-xl">
          {failed ? "Can't connect" : `Connect ${appName} to ${appConfig.appName}`}
        </CardTitle>
        {!failed && check && (
          <CardDescription>
            {check.scope === "alexa"
              ? `${appName} wants to add items to your ${appConfig.appName} shopping list and read it back to you. It can't see or change anything else.`
              : `${appName} wants to use ${appConfig.appName} as you. It will be able to see and change everything you can.`}
          </CardDescription>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {!check && !error && (
          <div className="flex justify-center py-4">
            <Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={1.5} />
          </div>
        )}
        {check?.status === "ok" && account && (
          <p className="text-center text-sm text-muted-foreground">
            Signed in as <span className="font-medium text-foreground">{account}</span>
          </p>
        )}
        {(failed || error) && (
          <div role="alert" className="flex items-start gap-2 text-sm text-destructive">
            <AlertCircle className="mt-0.5 size-4 shrink-0" strokeWidth={1.5} />
            <span>{failed || error}</span>
          </div>
        )}
      </CardContent>

      {check?.status === "ok" && (
        <CardFooter className="flex-col gap-2 sm:flex-row-reverse">
          <Button
            className="w-full sm:flex-1"
            onClick={() => decide("allow")}
            disabled={pending !== null}
          >
            {pending === "allow" && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
            Allow
          </Button>
          <Button
            variant="outline"
            className="w-full sm:flex-1"
            onClick={() => decide("deny")}
            disabled={pending !== null}
          >
            {pending === "deny" && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
            Cancel
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
