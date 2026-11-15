"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Loader2, PlugZap, Unplug } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { oauthApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";
import type { ConnectionDTO } from "@/types/oauth";

const CONNECTIONS_KEY = ["oauth-connections"] as const;

/** "ChatGPT", "ChatGPT and Amazon Alexa". */
const joinNames = (list: string[]) =>
  list.length > 1 ? `${list.slice(0, -1).join(", ")} and ${list[list.length - 1]}` : list.join("");

/** What each connected app can do, one sentence per kind of access. */
export function describeConnections(connections: ConnectionDTO[]): string {
  const unique = (scope: "mcp" | "alexa") =>
    Array.from(new Set(connections.filter((c) => (c.scope ?? "mcp") === scope).map((c) => c.client_name)));
  const full = unique("mcp");
  const shopping = unique("alexa");
  const sentences: string[] = [];
  if (full.length) sentences.push(`${joinNames(full)} can see and change your recipes, meal plan and shopping list.`);
  if (shopping.length) sentences.push(`${joinNames(shopping)} can add to and read your shopping list.`);
  return sentences.join(" ");
}

/**
 * ConnectedAppsCard — the apps connected to this account (ChatGPT through the
 * MCP connector, Alexa through account linking), with one button that
 * disconnects them all at once.
 */
export function ConnectedAppsCard() {
  const { getToken } = useAuth();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: CONNECTIONS_KEY,
    queryFn: async () => oauthApi.listConnections(await getToken()),
  });

  const disconnect = useMutation({
    mutationFn: async () => oauthApi.disconnectAll(await getToken()),
    onSuccess: () => {
      toast.success("Disconnected. Connected apps can no longer reach your account.");
      queryClient.invalidateQueries({ queryKey: CONNECTIONS_KEY });
    },
    onError: (error) => toast.error(getErrorMessage(error, "Couldn't disconnect")),
  });

  const [alexaCode, setAlexaCode] = useState("");
  const linkAlexa = useMutation({
    mutationFn: async (code: string) => oauthApi.linkAlexa(code, await getToken()),
    onSuccess: () => {
      toast.success("Alexa is connected. Try: “Alexa, tell Enchanted Spoon to add milk.”");
      setAlexaCode("");
      queryClient.invalidateQueries({ queryKey: CONNECTIONS_KEY });
    },
    onError: (error) => toast.error(getErrorMessage(error, "That code didn't work")),
  });
  const codeDigits = alexaCode.replace(/\D/g, "");

  const connections = data?.connections ?? [];
  const names = Array.from(new Set(connections.map((c) => c.client_name)));

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium text-foreground">
        <PlugZap strokeWidth={1.5} className="h-3.5 w-3.5 text-muted-foreground" />
        Connected Apps
      </div>
      <p className="text-xs text-muted-foreground">
        {isLoading
          ? "Checking for connected apps…"
          : names.length
            ? describeConnections(connections)
            : "No apps are connected. You can connect ChatGPT from its Apps settings, or Alexa from the Enchanted Spoon skill."}
      </p>
      {names.length > 0 && (
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={() => disconnect.mutate()}
          disabled={disconnect.isPending}
        >
          {disconnect.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
          ) : (
            <Unplug strokeWidth={1.5} className="h-4 w-4" />
          )}
          Disconnect {names.length === 1 ? names[0] : "all"}
        </Button>
      )}
      <form
        className="space-y-2 pt-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (codeDigits.length === 6) linkAlexa.mutate(codeDigits);
        }}
      >
        <label htmlFor="alexa-code" className="text-xs font-medium text-foreground">
          Connect Alexa
        </label>
        <p className="text-xs text-muted-foreground">
          Say “Alexa, open Enchanted Spoon” and enter the six-digit code it reads out.
        </p>
        <div className="flex gap-2">
          <Input
            id="alexa-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="123456"
            maxLength={9}
            value={alexaCode}
            onChange={(event) => setAlexaCode(event.target.value)}
            className="max-w-40"
          />
          <Button
            type="submit"
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={codeDigits.length !== 6 || linkAlexa.isPending}
          >
            {linkAlexa.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
            ) : (
              <Link2 strokeWidth={1.5} className="h-4 w-4" />
            )}
            Connect
          </Button>
        </div>
      </form>
    </div>
  );
}
