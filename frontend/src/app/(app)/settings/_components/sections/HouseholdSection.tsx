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
        A household shares one meal plan and one shopping list, kept on the owner&apos;s
        account. Recipes stay with the person who created them until they share each one.
        One Pro subscription on the owner covers members. Each person keeps their own
        monthly AI allowance.
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
  const [email, setEmail] = useState("");
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
        The meal plan and shopping list you see now are the household&apos;s, stored on the
        owner&apos;s account. Your own plan and list are kept and come back if you leave.
        Share individual recipes from a recipe page.{" "}
        {household.pro_covers_members
          ? "The owner's Pro plan covers members. Each person still has their own monthly AI allowance at Pro limits."
          : "If the owner subscribes to Pro, members get Pro access without paying separately. Each person keeps a separate monthly allowance."}
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
          <form
            className="space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              createInvite.mutate(email.trim() ? email.trim() : null, {
                onSuccess: () => {
                  setEmail("");
                  toast.success("Invite created. Copy the link to share it.");
                },
                onError: (error) => toast.error(errorMessage(error, "Could not create an invite")),
              });
            }}
          >
            <Label htmlFor="invite-email">Invite</Label>
            <Input
              id="invite-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="Optional email — we don't send it"
              disabled={createInvite.isPending}
            />
            <p className="text-xs text-muted-foreground">
              Leave the email blank for a link anyone can use. If you add one, only that
              account can redeem the code. Enchanted Spoon does not send email yet.
            </p>
            <Button type="submit" disabled={createInvite.isPending}>
              {createInvite.isPending && <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />}
              Create invite link
            </Button>
          </form>

          {household.invites.length > 0 && (
            <ul className="space-y-3">
              {household.invites.map((invite) => (
                <li key={invite.id} className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm text-foreground">{invite.code}</p>
                    <p className="text-xs text-muted-foreground">
                      {invite.email ? `Only ${invite.email}` : "Anyone with the link"} · expires{" "}
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
