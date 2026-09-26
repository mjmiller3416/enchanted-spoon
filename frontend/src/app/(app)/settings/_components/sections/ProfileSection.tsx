"use client";

import { User, Mail, Settings, Shield } from "lucide-react";
import { useUser, useClerk } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { SectionHeader } from "../SectionHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { DeleteAccountCard } from "../DeleteAccountCard";

// Account deletion runs through the app (it must cancel billing and remove app
// data first), so hide Clerk's own "Delete account" control in its profile modal
const userProfileProps = {
  appearance: { elements: { profileSection__danger: { display: "none" } } },
};

/**
 * ProfileSection displays the user's Clerk-managed profile information.
 * Profile data is read-only - users manage it through Clerk's account portal.
 */
export function ProfileSection() {
  const { user, isLoaded } = useUser();
  const { openUserProfile } = useClerk();

  // Loading state
  if (!isLoaded) {
    return (
      <Card>
        <CardContent className="pt-6">
          <SectionHeader
            icon={User}
            title="Account & Profile"
            description="Your account details and sign-in preferences"
          />
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-4 sm:gap-6">
              <Skeleton className="h-24 w-24 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Not signed in (shouldn't happen on protected routes)
  if (!user) {
    return (
      <Card>
        <CardContent className="pt-6">
          <SectionHeader
            icon={User}
            title="Account & Profile"
            description="Sign in to view your profile"
          />
          <p className="text-muted-foreground">
            Please sign in to access your profile settings.
          </p>
        </CardContent>
      </Card>
    );
  }

  const primaryEmail = user.emailAddresses.find(
    (email) => email.id === user.primaryEmailAddressId
  );
  const displayName = user.fullName || user.firstName || "User";
  const initials = displayName.charAt(0).toUpperCase();

  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={User}
          title="Account & Profile"
          description="Your account details and sign-in preferences"
        />

        <div className="space-y-6">
          {/* Avatar and Name Section */}
          <div className="flex flex-wrap items-center gap-4 sm:gap-6">
            <Avatar className="h-24 w-24 border-4 border-elevated">
              <AvatarImage src={user.imageUrl} alt={displayName} />
              <AvatarFallback className="bg-primary text-primary-foreground text-2xl">
                {initials}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-xl font-semibold text-foreground">
                  {displayName}
                </h3>
                <Badge variant="secondary" className="text-xs">
                  <Shield strokeWidth={1.5} className="h-3 w-3 mr-1" />
                  Verified
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Member since{" "}
                {new Date(user.createdAt!).toLocaleDateString("en-US", {
                  month: "long",
                  year: "numeric",
                })}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3 gap-2"
                onClick={() => openUserProfile(userProfileProps)}
              >
                <Settings strokeWidth={1.5} className="h-4 w-4" />
                Manage Profile
              </Button>
            </div>
          </div>

          <Separator />

          {/* Email Display */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Mail strokeWidth={1.5} className="h-3.5 w-3.5 text-muted-foreground" />
              Email Address
            </div>
            <div className="flex items-center gap-3">
              <div className="px-3 py-2 bg-elevated rounded-md text-foreground max-w-md min-w-0 break-words flex-1">
                {primaryEmail?.emailAddress || "No email set"}
              </div>
              {primaryEmail?.verification?.status === "verified" && (
                <Badge variant="outline" className="text-xs text-success border-success/30">
                  Verified
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Update your email in Manage Profile
            </p>
          </div>

          <Separator />

          {/* Account Security Info */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Shield strokeWidth={1.5} className="h-3.5 w-3.5 text-muted-foreground" />
              Account Security
            </div>
            <div className="bg-elevated rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Password & 2FA
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-2 h-8"
                  onClick={() => openUserProfile(userProfileProps)}
                >
                  <Settings strokeWidth={1.5} className="h-3 w-3" />
                  Manage
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Manage your password, two-factor authentication, and connected accounts
              </p>
            </div>
          </div>

          <Separator />

          <DeleteAccountCard />
        </div>
      </CardContent>
    </Card>
  );
}
