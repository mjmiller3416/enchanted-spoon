"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, Users } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { ApiError } from "@/lib/api";
import {
  useCreateHousehold,
  useCreateHouseholdInvite,
  useDissolveHousehold,
  useHousehold,
  useJoinHousehold,
  useLeaveHousehold,
  useRemoveHouseholdMember,
  useRevokeHouseholdInvite,
  useTransferHousehold,
} from "@/hooks/api";
import type { Household } from "@/types/household";
import { SectionHeader } from "../SectionHeader";

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError && error.message) return error.message;
  return fallback;
}

function inviteLink(code: string): string {
  return `${window.location.origin}/settings?section=household&invite=${encodeURIComponent(code)}`;
}

export function HouseholdSection() {
  const searchParams = useSearchParams();
  const householdQuery = useHousehold();
  const household = householdQuery.data?.household ?? null;

  if (householdQuery.isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <SectionHeader
            icon={Users}
            title="Household"
            description="Share recipes, the meal plan, and the shopping list"
          />
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />
            Loading household
          </div>
        </CardContent>
      </Card>
    );
  }

  if (householdQuery.isError) {
    return (
      <Card>
        <CardContent className="pt-6">
          <SectionHeader
            icon={Users}
            title="Household"
            description="Share recipes, the meal plan, and the shopping list"
          />
          <p className="text-sm text-destructive">The household could not be loaded.</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => void householdQuery.refetch()}
          >
            Try again
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={Users}
          title="Household"
          description="Share recipes, the meal plan, and the shopping list"
        />
        {household ? (
          <HouseholdHome household={household} />
        ) : (
          <HouseholdSetup key={searchParams.get("invite") ?? ""} initialCode={searchParams.get("invite") ?? ""} />
        )}
      </CardContent>
    </Card>
  );
}

function HouseholdSetup({ initialCode }: { initialCode: string }) {
  const [name, setName] = useState("");
  const [code, setCode] = useState(initialCode);
  const create = useCreateHousehold();
  const join = useJoinHousehold();

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        A household is the owner&apos;s kitchen: one meal plan and one shopping list, for
        up to 6 people. Recipes stay with the person who created them until they share
        each one. Once a second person joins, photos, chat, suggestions, and imports
        share one allowance on the owner&apos;s account.
      </p>

      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          create.mutate(name.trim(), {
            onSuccess: () => toast.success("Household created"),
            onError: (error) => toast.error(errorMessage(error, "Could not create the household")),
          });
        }}
      >
        <Label htmlFor="household-name">Household name</Label>
        <Input
          id="household-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="The Miller kitchen"
          maxLength={80}
          disabled={create.isPending}
        />
        <Button type="submit" disabled={create.isPending || !name.trim()}>
          {create.isPending && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
          Create household
        </Button>
      </form>

      <Separator />

      <form
        className="space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          join.mutate(code.trim(), {
            onSuccess: () => toast.success("You joined the household"),
            onError: (error) => toast.error(errorMessage(error, "Could not join with that code")),
          });
        }}
      >
        <Label htmlFor="household-code">Invite code</Label>
        <Input
          id="household-code"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="Paste a code"
          disabled={join.isPending}
        />
        <Button type="submit" variant="outline" disabled={join.isPending || code.trim().length < 4}>
          {join.isPending && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
          Join household
        </Button>
      </form>
    </div>
  );
}

function HouseholdHome({ household }: { household: Household }) {
  const isOwner = household.role === "owner";
  const createInvite = useCreateHouseholdInvite();
  const revoke = useRevokeHouseholdInvite();
  const leave = useLeaveHousehold();
  const dissolve = useDissolveHousehold();
  const remove = useRemoveHouseholdMember();
  const transfer = useTransferHousehold();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-lg font-semibold text-foreground">{household.name}</h3>
        <Badge variant="secondary">{isOwner ? "Owner" : "Member"}</Badge>
        {household.pro_covers_members && <Badge variant="outline">Pro included</Badge>}
      </div>

      <p className="text-sm text-muted-foreground">
        This is the owner&apos;s kitchen. The meal plan and shopping list live on the
        owner&apos;s account, and they come back to you as your own if you leave.
        Share individual recipes from a recipe page. With two or more people, photos,
        chat, suggestions, and imports share one allowance — see Plan &amp; Billing for what&apos;s left.
      </p>

      <div className="space-y-3">
        <h4 className="text-sm font-medium text-foreground">People</h4>
        <ul className="space-y-3">
          {household.members.map((member) => (
            <li key={member.user_id} className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm text-foreground">{member.name || member.email}</p>
                <p className="text-xs text-muted-foreground">
                  {member.email} · {member.role}
                </p>
              </div>
              {isOwner && member.role !== "owner" && (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={transfer.isPending}
                    onClick={() => {
                      const label = member.name || member.email;
                      if (!window.confirm(`Make ${label} the owner? The meal plan and shopping list move to their account.`)) {
                        return;
                      }
                      transfer.mutate(member.user_id, {
                        onSuccess: () => toast.success("Ownership transferred"),
                        onError: (error) =>
                          toast.error(errorMessage(error, "Could not transfer ownership")),
                      });
                    }}
                  >
                    Make owner
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={remove.isPending}
                    aria-label={`Remove ${member.name || member.email}`}
                    onClick={() =>
                      remove.mutate(member.user_id, {
                        onSuccess: () => toast.success("Member removed"),
                        onError: (error) => toast.error(errorMessage(error, "Could not remove them")),
                      })
                    }
                  >
                    Remove
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      {isOwner && (
        <>
          <Separator />
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Create a link or code and share it. Anyone with it can join until it expires.
            </p>
            <Button
              type="button"
              disabled={createInvite.isPending}
              onClick={() =>
                createInvite.mutate(null, {
                  onSuccess: () => toast.success("Invite created. Copy the link or share the code."),
                  onError: (error) => toast.error(errorMessage(error, "Could not create an invite")),
                })
              }
            >
              {createInvite.isPending && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
              Create invite link
            </Button>
          </div>

          {household.invites.length > 0 && (
            <ul className="space-y-3">
              {household.invites.map((invite) => (
                <li key={invite.id} className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm text-foreground">{invite.code}</p>
                    <p className="text-xs text-muted-foreground">
                      Anyone with the link or code · expires{" "}
                      {new Date(invite.expires_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        void navigator.clipboard.writeText(inviteLink(invite.code)).then(
                          () => toast.success("Invite link copied"),
                          () => toast.error("Could not copy the link"),
                        );
                      }}
                    >
                      Copy link
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      aria-label={`Revoke invite ${invite.code}`}
                      disabled={revoke.isPending}
                      onClick={() =>
                        revoke.mutate(invite.id, {
                          onSuccess: () => toast.success("Invite revoked"),
                          onError: (error) => toast.error(errorMessage(error, "Could not revoke it")),
                        })
                      }
                    >
                      Revoke
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <Separator />

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={leave.isPending}
          onClick={() =>
            leave.mutate(undefined, {
              onSuccess: () => toast.success("You left the household"),
              onError: (error) => toast.error(errorMessage(error, "Could not leave")),
            })
          }
        >
          {leave.isPending && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
          Leave household
        </Button>
        {isOwner && (
          <Button
            type="button"
            variant="outline"
            disabled={dissolve.isPending}
            onClick={() => {
              if (!window.confirm("Delete this household for everyone? Shared recipes stay with their owners. The meal plan and shopping list stay on your account.")) {
                return;
              }
              dissolve.mutate(undefined, {
                onSuccess: () => toast.success("Household deleted"),
                onError: (error) => toast.error(errorMessage(error, "Could not delete the household")),
              });
            }}
          >
            {dissolve.isPending && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
            Delete household
          </Button>
        )}
      </div>
    </div>
  );
}
