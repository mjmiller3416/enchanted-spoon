"use client";

import { useState, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  CalendarDays,
  BookOpen,
  House,
  ShoppingCart,
  EllipsisVertical,
  Plus,
  Settings,
  MessageSquarePlus,
  Moon,
  Sparkles,
  Sun,
  LogOut,
  Shield,
  UtensilsCrossed,
  LucideIcon,
} from "lucide-react";
import { useUser, useClerk } from "@clerk/nextjs";
import { SafeLink } from "@/components/common/SafeLink";
import { FeedbackDialog } from "@/components/common/FeedbackDialog";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { useShoppingList, useRefreshShoppingList, useCurrentUser } from "@/hooks/api";
import { useTheme } from "@/hooks/ui";
import { useRecipeWizardDialog } from "@/lib/providers/RecipeWizardProvider";

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  hasBadge?: boolean;
}

const navigation: NavItem[] = [
  { name: "Home", href: "/dashboard", icon: House },
  { name: "Planner", href: "/meal-planner", icon: CalendarDays },
  { name: "Recipes", href: "/recipes", icon: BookOpen },
  { name: "Shopping", href: "/shopping-list", icon: ShoppingCart, hasBadge: true },
];

interface MobileBottomNavProps {
  onOpenAssistant?: () => void;
}

export function MobileBottomNav({ onOpenAssistant }: MobileBottomNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useUser();
  const { signOut } = useClerk();
  const { isAdmin } = useCurrentUser();
  const { openWizard } = useRecipeWizardDialog();
  const { resolvedTheme, toggleTheme } = useTheme();

  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  // Use React Query hook with automatic token injection
  const { data: shoppingData } = useShoppingList();
  const refreshShoppingList = useRefreshShoppingList();

  // Calculate remaining items from query data
  const shoppingCount = shoppingData
    ? shoppingData.total_items - shoppingData.checked_items
    : 0;

  useEffect(() => {
    window.addEventListener("shopping-list-updated", refreshShoppingList);
    return () => {
      window.removeEventListener("shopping-list-updated", refreshShoppingList);
    };
  }, [refreshShoppingList]);

  const handleSignOut = async () => {
    setIsMoreOpen(false);
    await signOut();
    router.push("/sign-in");
  };

  const handleMenuAction = (action: () => void) => {
    setIsMoreOpen(false);
    action();
  };

  const displayName = user?.fullName || user?.firstName || "Account";
  const email = user?.primaryEmailAddress?.emailAddress || "";
  const initials = (() => {
    if (!user) return "?";
    const first = user.firstName || "";
    const last = user.lastName || "";
    if (first && last) return `${first[0]}${last[0]}`.toUpperCase();
    if (first) return first.slice(0, 2).toUpperCase();
    if (email) return email[0].toUpperCase();
    return "?";
  })();

  return (
    <>
      <nav
        className={cn(
          // Only visible on mobile
          "md:hidden",
          // Fixed at bottom
          "fixed bottom-0 left-0 right-0 z-50",
          // Background and border
          "bg-sidebar border-t border-border",
          // Safe area padding for devices with home indicators
          "pb-[env(safe-area-inset-bottom,0px)]",
          // Hide when printing
          "print:hidden"
        )}
      >
        <div className="flex items-center justify-around h-16">
          {navigation.map((item) => {
            // Sections highlight on their detail pages too (e.g. /recipes/42)
            const isActive =
              pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <SafeLink
                key={item.href}
                href={item.href}
                className={cn(
                  // Layout
                  "flex flex-col items-center justify-center",
                  // Touch-friendly size
                  "min-w-14 h-14 px-1",
                  // Transitions
                  "transition-colors duration-200",
                  // Text color
                  isActive ? "text-primary" : "text-muted-foreground",
                  // Touch feedback
                  "active:scale-95"
                )}
              >
                {/* Icon with optional badge */}
                <div className="relative">
                  <item.icon
                    className={cn("h-6 w-6", isActive && "text-primary")}
                    strokeWidth={isActive ? 2 : 1.5}
                  />
                  {/* Badge for shopping list */}
                  {item.hasBadge && shoppingCount > 0 && (
                    <div
                      className={cn(
                        "absolute -top-1 -right-2",
                        "min-w-4 h-4 px-1",
                        "flex items-center justify-center",
                        "rounded-full text-2xs font-semibold",
                        "bg-error text-white"
                      )}
                    >
                      {shoppingCount > 99 ? "99+" : shoppingCount}
                    </div>
                  )}
                </div>

                {/* Label */}
                <span
                  className={cn(
                    "text-2xs mt-1 font-medium",
                    isActive && "text-primary"
                  )}
                >
                  {item.name}
                </span>
              </SafeLink>
            );
          })}

          {/* More Button */}
          <Button
            variant="ghost"
            onClick={() => setIsMoreOpen(true)}
            className={cn(
              // Layout
              "flex flex-col items-center justify-center",
              // Touch-friendly size
              "min-w-14 h-14 px-1 rounded-none",
              // Transitions
              "transition-colors duration-200",
              // Text color
              "text-muted-foreground hover:text-primary hover:bg-transparent",
              // Touch feedback
              "active:scale-95"
            )}
          >
            <EllipsisVertical className="h-6 w-6" strokeWidth={1.5} />
            <span className="text-2xs mt-1 font-medium">More</span>
          </Button>
        </div>
      </nav>

      {/* More Menu Sheet */}
      <Sheet open={isMoreOpen} onOpenChange={setIsMoreOpen}>
        <SheetContent
          side="bottom"
          className="rounded-t-2xl p-0 [&>button[data-slot=sheet-close]]:hidden"
        >
          <SheetTitle className="sr-only">Menu</SheetTitle>

          {/* Drag handle */}
          <div className="flex justify-center pt-3 pb-1">
            <div className="w-10 h-1 rounded-full bg-border" />
          </div>

          {/* User profile header */}
          {user && (
            <div className="flex items-center gap-3 px-5 py-3 border-b border-border">
              <Avatar className="h-10 w-10">
                <AvatarImage src={user.imageUrl} alt={displayName} />
                <AvatarFallback className="bg-primary/10 text-primary font-medium">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {displayName}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {email}
                </p>
              </div>
            </div>
          )}

          {/* Menu items */}
          <div className="py-2 pb-[env(safe-area-inset-bottom,8px)]">
            <Button
              variant="ghost"
              onClick={() => handleMenuAction(() => openWizard())}
              className="flex items-center justify-start gap-3 px-5 py-3 w-full h-auto rounded-none text-sm text-foreground"
            >
              <Plus className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              Add Recipe
            </Button>

            <Button
              variant="ghost"
              onClick={() =>
                handleMenuAction(() => router.push("/meal-planner?addMeal=1"))
              }
              className="flex items-center justify-start gap-3 px-5 py-3 w-full h-auto rounded-none text-sm text-foreground"
            >
              <UtensilsCrossed className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              Add Meal
            </Button>

            <div className="h-px bg-border mx-5 my-1" />

            <SafeLink
              href="/settings"
              onClick={() => setIsMoreOpen(false)}
              className="flex items-center gap-3 px-5 py-3 text-sm text-foreground active:bg-accent transition-colors"
            >
              <Settings className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              Settings
            </SafeLink>

            {/* Theme flips in place — sheet stays open so the change is visible */}
            <Button
              variant="ghost"
              onClick={toggleTheme}
              className="flex items-center justify-start gap-3 px-5 py-3 w-full h-auto rounded-none text-sm text-foreground"
            >
              {resolvedTheme === "dark" ? (
                <Sun className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              ) : (
                <Moon className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              )}
              {resolvedTheme === "dark" ? "Light mode" : "Dark mode"}
            </Button>

            {isAdmin && (
              <SafeLink
                href="/admin"
                onClick={() => setIsMoreOpen(false)}
                className="flex items-center gap-3 px-5 py-3 text-sm text-foreground active:bg-accent transition-colors"
              >
                <Shield className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
                Admin Panel
              </SafeLink>
            )}

            <Button
              variant="ghost"
              onClick={() => handleMenuAction(() => setFeedbackOpen(true))}
              className="flex items-center justify-start gap-3 px-5 py-3 w-full h-auto rounded-none text-sm text-foreground"
            >
              <MessageSquarePlus className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              Submit Feedback
            </Button>

            {onOpenAssistant && (
              <Button
                variant="ghost"
                onClick={() => handleMenuAction(onOpenAssistant)}
                className="flex items-center justify-start gap-3 px-5 py-3 w-full h-auto rounded-none text-sm text-foreground"
              >
                <Sparkles className="h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
                Ask the Genie
              </Button>
            )}

            <div className="h-px bg-border mx-5 my-1" />

            <Button
              variant="ghost"
              onClick={handleSignOut}
              className="flex items-center justify-start gap-3 px-5 py-3 w-full h-auto rounded-none text-sm text-destructive hover:text-destructive"
            >
              <LogOut className="h-5 w-5" strokeWidth={1.5} />
              Sign out
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Feedback Dialog */}
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />
    </>
  );
}
