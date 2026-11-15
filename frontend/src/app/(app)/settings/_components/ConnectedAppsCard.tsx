"use client";

import { useAuth } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, PlugZap, Unplug } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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
    </div>
  );
}
