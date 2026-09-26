"use client";

import { useState } from "react";
import { useAuth, useClerk } from "@clerk/nextjs";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Loader2, UserX } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { adminApi } from "@/lib/api";
import { getErrorMessage } from "@/lib/utils";

const CONFIRM_PHRASE = "DELETE";

/**
 * DeleteAccountCard — permanently delete the signed-in account. The backend
 * cancels any subscription first, removes all data, then the Clerk sign-in.
 */
export function DeleteAccountCard() {
  const { getToken } = useAuth();
  const { signOut } = useClerk();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const handleOpenChange = (next: boolean) => {
    if (isDeleting) return;
    setOpen(next);
    if (!next) setConfirmText("");
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const token = await getToken();
      await adminApi.deleteCurrentUser(token);
      queryClient.clear();
      toast.success("Your account has been deleted.");
      await signOut({ redirectUrl: "/" });
    } catch (error) {
      toast.error(getErrorMessage(error, "Failed to delete your account"));
      setIsDeleting(false);
    }
  };

  return (
    <>
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-medium text-destructive">
          <UserX strokeWidth={1.5} className="h-3.5 w-3.5" />
          Delete Account
        </div>
        <p className="text-xs text-muted-foreground">
          Permanently delete your account, cancel any subscription, and remove all of your
          recipes, meals, menus, shopping lists, and settings.
        </p>
        <Button variant="destructive" size="sm" className="gap-2" onClick={() => setOpen(true)}>
          <UserX strokeWidth={1.5} className="h-4 w-4" />
          Delete Account
        </Button>
      </div>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle strokeWidth={1.5} className="h-5 w-5" />
              Delete your account?
            </DialogTitle>
            <DialogDescription>
              This permanently deletes your account and everything in it. Any Pro subscription is
              cancelled immediately. This can&apos;t be undone — download a backup from Data
              Management first if you might want your recipes later.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="delete-account-confirm">
              Type {CONFIRM_PHRASE} to confirm
            </Label>
            <Input
              id="delete-account-confirm"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              autoComplete="off"
              disabled={isDeleting}
            />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isDeleting}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting || confirmText.trim() !== CONFIRM_PHRASE}
              className="gap-2"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <UserX strokeWidth={1.5} className="h-4 w-4" />
              )}
              Delete Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
