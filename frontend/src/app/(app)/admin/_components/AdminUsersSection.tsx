"use client";

import { useState } from "react";
import {
  Shield,
  Trash2,
  UserPlus,
  UserMinus,
  ShieldCheck,
  ShieldOff,
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { SectionHeader } from "./SectionHeader";
import { ConfirmDialog } from "./ConfirmDialog";
import { GrantProDialog } from "./GrantProDialog";
import {
  useAdminUsers,
  useGrantPro,
  useRevokePro,
  useToggleAdmin,
  useDeleteUser,
} from "@/hooks/api";
import type { AdminUserDTO } from "@/types/admin";

function getAccessBadge(user: AdminUserDTO) {
  if (user.is_admin) {
    return <Badge variant="default">Admin</Badge>;
  }
  if (user.has_pro_access) {
    return <Badge variant="secondary">Pro</Badge>;
  }
  return <Badge variant="outline">Free</Badge>;
}

function getInitials(name: string | null, email: string): string {
  if (name) {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }
  return email[0].toUpperCase();
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function AdminUsersSection() {
  const [page, setPage] = useState(0);
  const limit = 20;
  const { data, isLoading } = useAdminUsers(page * limit, limit);

  const grantPro = useGrantPro();
  const revokePro = useRevokePro();
  const toggleAdmin = useToggleAdmin();
  const deleteUser = useDeleteUser();

  // Dialog state
  const [grantProTarget, setGrantProTarget] = useState<AdminUserDTO | null>(null);
  const [revokeProTarget, setRevokeProTarget] = useState<AdminUserDTO | null>(null);
  const [toggleAdminTarget, setToggleAdminTarget] = useState<AdminUserDTO | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminUserDTO | null>(null);

  const handleGrantPro = (grantedProUntil: string, grantedBy: string) => {
    if (!grantProTarget) return;
    grantPro.mutate(
      { userId: grantProTarget.id, data: { granted_pro_until: grantedProUntil, granted_by: grantedBy } },
      {
        onSuccess: () => {
          toast.success(`Pro access granted to ${grantProTarget.name || grantProTarget.email}`);
          setGrantProTarget(null);
        },
        onError: (error) => toast.error(error.message),
      },
    );
  };

  const handleRevokePro = () => {
    if (!revokeProTarget) return;
    revokePro.mutate(revokeProTarget.id, {
      onSuccess: () => {
        toast.success(`Pro access revoked from ${revokeProTarget.name || revokeProTarget.email}`);
        setRevokeProTarget(null);
      },
      onError: (error) => toast.error(error.message),
    });
  };

  const handleToggleAdmin = () => {
    if (!toggleAdminTarget) return;
    const newIsAdmin = !toggleAdminTarget.is_admin;
    toggleAdmin.mutate(
      { userId: toggleAdminTarget.id, data: { is_admin: newIsAdmin } },
      {
        onSuccess: () => {
          toast.success(
            newIsAdmin
              ? `${toggleAdminTarget.name || toggleAdminTarget.email} is now an admin`
              : `Admin access removed from ${toggleAdminTarget.name || toggleAdminTarget.email}`,
          );
          setToggleAdminTarget(null);
        },
        onError: (error) => toast.error(error.message),
      },
    );
  };

  const handleDeleteUser = () => {
    if (!deleteTarget) return;
    deleteUser.mutate(deleteTarget.id, {
      onSuccess: () => {
        toast.success(`User ${deleteTarget.name || deleteTarget.email} deleted`);
        setDeleteTarget(null);
      },
      onError: (error) => toast.error(error.message),
    });
  };

  const totalPages = data ? Math.ceil(data.total / limit) : 0;

  return (
    <>
      <Card>
        <CardContent className="pt-6">
          <SectionHeader
            icon={Shield}
            title="User Management"
            description="View and manage all registered users"
          />

          {isLoading ? (
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-56" />
                  </div>
                  <Skeleton className="h-6 w-16" />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {data?.items.map((user) => (
                <div
                  key={user.id}
                  className="flex items-center gap-4 p-3 rounded-xl hover:bg-hover transition-colors"
                >
                  <Avatar className="h-10 w-10">
                    <AvatarImage src={user.avatar_url || undefined} />
                    <AvatarFallback className="bg-elevated text-muted-foreground text-sm">
                      {getInitials(user.name, user.email)}
                    </AvatarFallback>
                  </Avatar>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {user.name || "No name"}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {user.email}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    {getAccessBadge(user)}

                    {user.granted_pro_until ? (
                      <span className="text-xs text-muted-foreground hidden sm:inline">
                        until {formatDate(user.granted_pro_until)}
                      </span>
                    ) : user.access_reason === "subscription" &&
                      user.subscription_ends_at ? (
                      <span className="text-xs text-muted-foreground hidden sm:inline">
                        renews {formatDate(user.subscription_ends_at)}
                      </span>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-1 flex-shrink-0">
                    {!user.has_pro_access ? (
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label="Grant pro access"
                        onClick={() => setGrantProTarget(user)}
                      >
                        <UserPlus className="h-4 w-4" strokeWidth={1.5} />
                      </Button>
                    ) : user.granted_pro_until ? (
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label="Revoke pro access"
                        onClick={() => setRevokeProTarget(user)}
                      >
                        <UserMinus className="h-4 w-4" strokeWidth={1.5} />
                      </Button>
                    ) : null}

                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label={user.is_admin ? "Remove admin access" : "Grant admin access"}
                      onClick={() => setToggleAdminTarget(user)}
                    >
                      {user.is_admin ? (
                        <ShieldOff className="h-4 w-4" strokeWidth={1.5} />
                      ) : (
                        <ShieldCheck className="h-4 w-4" strokeWidth={1.5} />
                      )}
                    </Button>

                    <Button
                      size="icon"
                      variant="ghost"
                      aria-label="Delete user"
                      onClick={() => setDeleteTarget(user)}
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                    </Button>
                  </div>
                </div>
              ))}

              {data?.items.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No users found.
                </p>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <>
                  <Separator />
                  <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-muted-foreground">
                      {data?.total} users total
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => Math.max(0, p - 1))}
                        disabled={page === 0}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage((p) => p + 1)}
                        disabled={page >= totalPages - 1}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialogs */}
      <GrantProDialog
        open={!!grantProTarget}
        onOpenChange={(open) => !open && setGrantProTarget(null)}
        userName={grantProTarget?.name ?? null}
        onConfirm={handleGrantPro}
        isLoading={grantPro.isPending}
      />

      <ConfirmDialog
        open={!!revokeProTarget}
        onOpenChange={(open) => !open && setRevokeProTarget(null)}
        title="Revoke Pro Access"
        description={`Remove granted pro access from ${revokeProTarget?.name || revokeProTarget?.email || "this user"}?`}
        confirmLabel="Revoke"
        onConfirm={handleRevokePro}
        isLoading={revokePro.isPending}
      />

      <ConfirmDialog
        open={!!toggleAdminTarget}
        onOpenChange={(open) => !open && setToggleAdminTarget(null)}
        title={toggleAdminTarget?.is_admin ? "Remove Admin Access" : "Grant Admin Access"}
        description={
          toggleAdminTarget?.is_admin
            ? `Remove admin access from ${toggleAdminTarget?.name || toggleAdminTarget?.email || "this user"}?`
            : `Grant admin access to ${toggleAdminTarget?.name || toggleAdminTarget?.email || "this user"}? They will have full access to the admin panel.`
        }
        confirmLabel={toggleAdminTarget?.is_admin ? "Remove Admin" : "Make Admin"}
        onConfirm={handleToggleAdmin}
        isLoading={toggleAdmin.isPending}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete User"
        description={`Permanently delete ${deleteTarget?.name || deleteTarget?.email || "this user"} and all their data? This cannot be undone.`}
        confirmLabel="Delete User"
        onConfirm={handleDeleteUser}
        isLoading={deleteUser.isPending}
      />
    </>
  );
}
