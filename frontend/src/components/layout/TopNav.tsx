"use client";

import { useState, useEffect, useCallback, useSyncExternalStore } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useUser, useClerk } from "@clerk/nextjs";
import Link from "next/link";
import {
  LayoutDashboard,
  CalendarDays,
  BookOpen,
  ShoppingCart,
  Plus,
  Menu,
  Moon,
  Sun,
  UtensilsCrossed,
  Settings,
  LogOut,
  ChevronDown,
  MessageSquarePlus,
  Sparkles,
  Shield,
  LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { SafeLink } from "@/components/common/SafeLink";
import { Logo } from "@/components/layout/Logo";
import { FeedbackDialog } from "@/components/common/FeedbackDialog";
import { ChangelogDialog } from "@/components/common/ChangelogDialog";
import { ChangelogPopover } from "@/components/common/ChangelogPopover";
import { CHANGELOG_TOTAL_ITEMS } from "@/data/changelog";
import { appConfig } from "@/lib/config";
import { cn } from "@/lib/utils";
import { useShoppingList, useRefreshShoppingList, useCurrentUser } from "@/hooks/api";
import { useTheme } from "@/hooks/ui";
import { useNavActions } from "@/lib/providers/NavActionsProvider";
import { useRecipeWizardDialog } from "@/lib/providers/RecipeWizardProvider";

// ─────────────────────────────────────────────────────────────────────────────
// TopNavLink — Inline navigation link for the top nav bar
// ─────────────────────────────────────────────────────────────────────────────

interface TopNavLinkProps {
  icon: LucideIcon;
  label: string;
  href: string;
  isActive?: boolean;
  badge?: number;
}

function TopNavLink({
  icon: Icon,
  label,
  href,
  isActive = false,
  badge,
}: TopNavLinkProps) {
  return (
    <SafeLink
      href={href}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium",
        "transition-colors duration-200",
        isActive
          ? "text-primary bg-primary/10"
          : "text-muted-foreground hover:text-foreground hover:bg-hover/50"
      )}
    >
      <Icon className="h-4 w-4" strokeWidth={isActive ? 2 : 1.5} />
      <span>{label}</span>

      {badge !== undefined && badge > 0 && (
        <div
          className={cn(
            "min-w-5 h-5 px-1.5",
            "flex items-center justify-center",
            "rounded-full text-xs font-semibold",
            "bg-error/20 border border-error/30 text-error"
          )}
        >
          {badge > 99 ? "99+" : badge}
        </div>
      )}
    </SafeLink>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NavButton — Sheet navigation button (hamburger menu items)
// ─────────────────────────────────────────────────────────────────────────────

interface NavButtonProps {
  icon: LucideIcon;
  label: string;
  href: string;
  isActive?: boolean;
  badge?: number;
  onClick?: () => void;
}

function NavButton({
  icon: Icon,
  label,
  href,
  isActive = false,
  badge,
  onClick,
}: NavButtonProps) {
  return (
    <SafeLink
      href={href}
      onClick={onClick}
      className={cn(
        // Base layout
        "flex items-center gap-3 px-3 py-3 rounded-xl relative group",
        // Transitions for smooth interactions
        "transition-all duration-200 ease-physical",
        // Text colors
        "text-muted-foreground hover:text-foreground",
        // Hover background
        "hover:bg-hover/70",
        // Hover micro-interaction: slide right
        "hover:translate-x-1",
        // Press feedback
        "active:scale-[0.98]",
        // Active state
        isActive && "text-primary-light bg-primary/20 font-medium"
      )}
    >
      {/* Active indicator bar */}
      <div
        className={cn(
          "absolute left-0 top-1/2 -translate-y-1/2",
          "w-1 rounded-full bg-primary",
          "transition-all duration-200",
          isActive ? "h-6 opacity-100" : "h-0 opacity-0"
        )}
      />

      {/* Icon container with hover background */}
      <div
        className={cn(
          "relative p-2 rounded-lg",
          "transition-colors duration-200",
          isActive
            ? "bg-primary/30"
            : "group-hover:bg-hover/50"
        )}
      >
        <Icon className="h-5 w-5" strokeWidth={isActive ? 2 : 1.5} />
        {/* Glow effect when active */}
        {isActive && (
          <div className="absolute inset-0 bg-primary/20 rounded-lg blur-sm" />
        )}
      </div>

      {/* Label */}
      <span className="text-sm font-medium">{label}</span>

      {/* Badge (count) */}
      {badge !== undefined && badge > 0 && (
        <div
          className={cn(
            "ml-auto min-w-5 h-5 px-2",
            "flex items-center justify-center",
            "rounded-full text-xs font-semibold",
            "bg-error/20 border border-error/30 text-error"
          )}
        >
          {badge > 99 ? "99+" : badge}
        </div>
      )}
    </SafeLink>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TopNavAddMenu — Hover-activated "Add" dropdown in the top nav
// ─────────────────────────────────────────────────────────────────────────────

function TopNavAddMenu() {
  const router = useRouter();
  const { openWizard, isOpen: wizardOpen } = useRecipeWizardDialog();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className={cn(
            "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium",
            "transition-colors duration-200",
            wizardOpen
              ? "text-primary bg-primary/10"
              : "text-muted-foreground hover:text-foreground hover:bg-hover/50"
          )}
        >
          <Plus className="h-4 w-4" strokeWidth={wizardOpen ? 2 : 1.5} />
          <span>Add</span>
          <ChevronDown className="h-3.5 w-3.5" strokeWidth={1.5} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="min-w-32">
        <DropdownMenuItem onClick={() => openWizard()} className="gap-2">
          <BookOpen className="h-4 w-4" strokeWidth={1.5} />
          Add Recipe
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => router.push("/meal-planner?addMeal=1")}
          className="gap-2"
        >
          <UtensilsCrossed className="h-4 w-4" strokeWidth={1.5} />
          Add Meal
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TopNavUserMenu — User avatar dropdown with settings and sign-out
// ─────────────────────────────────────────────────────────────────────────────

interface TopNavUserMenuProps {
  onOpenAssistant?: () => void;
  onOpenFeedback?: () => void;
}

function TopNavUserMenu({ onOpenAssistant, onOpenFeedback }: TopNavUserMenuProps) {
  const { user, isLoaded } = useUser();
  const { signOut } = useClerk();
  const router = useRouter();
  const { isAdmin } = useCurrentUser();

  const handleSignOut = async () => {
    await signOut();
    router.push("/sign-in");
  };

  const getInitials = () => {
    if (!user) return "?";
    const firstName = user.firstName || "";
    const lastName = user.lastName || "";
    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase();
    }
    if (firstName) {
      return firstName.slice(0, 2).toUpperCase();
    }
    if (user.primaryEmailAddress?.emailAddress) {
      return user.primaryEmailAddress.emailAddress[0].toUpperCase();
    }
    return "?";
  };

  if (!isLoaded) {
    return <Skeleton className="h-8 w-8 rounded-full" />;
  }

  if (!user) {
    return (
      <Link href="/sign-in">
        <Button variant="ghost" size="icon" aria-label="Sign in">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-muted text-muted-foreground text-xs">
              ?
            </AvatarFallback>
          </Avatar>
        </Button>
      </Link>
    );
  }

  const displayName = user.fullName || user.firstName || "Account";
  const email = user.primaryEmailAddress?.emailAddress || "";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex items-center gap-1.5 px-1.5 py-1 h-auto rounded-full"
          aria-label="User menu"
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src={user.imageUrl} alt={displayName} />
            <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
              {getInitials()}
            </AvatarFallback>
          </Avatar>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" side="bottom" className="w-64">
        <DropdownMenuLabel className="font-normal">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              <AvatarImage src={user.imageUrl} alt={displayName} />
              <AvatarFallback className="bg-primary/10 text-primary font-medium">
                {getInitials()}
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
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        <DropdownMenuItem asChild>
          <Link
            href="/settings"
            className="flex items-center gap-2 cursor-pointer"
          >
            <Settings className="h-4 w-4" />
            Settings
          </Link>
        </DropdownMenuItem>

        {isAdmin && (
          <DropdownMenuItem asChild>
            <Link
              href="/admin"
              className="flex items-center gap-2 cursor-pointer"
            >
              <Shield className="h-4 w-4" />
              Admin Panel
            </Link>
          </DropdownMenuItem>
        )}

        <DropdownMenuItem
          onClick={onOpenFeedback}
          className="flex items-center gap-2 cursor-pointer"
        >
          <MessageSquarePlus className="h-4 w-4" />
          Submit Feedback
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={onOpenAssistant}
          className="flex items-center gap-2 cursor-pointer"
        >
          <Sparkles className="h-4 w-4" />
          Ask the Genie
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          onClick={handleSignOut}
          className="flex items-center gap-2 cursor-pointer text-destructive focus:text-destructive"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TopNav — Main top navigation bar (visible on md+)
// ─────────────────────────────────────────────────────────────────────────────

// Hydration detector: false during SSR/hydration render, true after mount —
// gates client-only UI (theme icon, changelog badge) without a setState effect
const emptySubscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

const navigation = [
  { name: "Home", href: "/dashboard", icon: LayoutDashboard },
  { name: "Meal Planner", href: "/meal-planner", icon: CalendarDays },
  { name: "Recipes", href: "/recipes", icon: BookOpen },
  { name: "Shopping List", href: "/shopping-list", icon: ShoppingCart, hasBadge: true },
];

interface TopNavProps {
  onOpenAssistant: () => void;
}

export function TopNav({ onOpenAssistant }: TopNavProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { actions: navActions, isPinned } = useNavActions();
  const { openWizard } = useRecipeWizardDialog();

  // Sheet state (hamburger menu for md-to-lg)
  const [sheetOpen, setSheetOpen] = useState(false);

  // Dialog state
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [changelogOpen, setChangelogOpen] = useState(false);
  const [changelogBadgeDismissed, setChangelogBadgeDismissed] = useState(false);
  const [changelogCountReset, setChangelogCountReset] = useState(false);
  const [changelogScrollTo, setChangelogScrollTo] = useState<number | null>(null);

  // Theme (shared model — persists via the settings store)
  const { resolvedTheme, toggleTheme } = useTheme();

  // Client-side state (lazy initializers read localStorage without triggering cascading renders)
  const [changelogNewItems] = useState(() => {
    if (typeof window === "undefined") return 0;
    const lastSeenCount = parseInt(
      localStorage.getItem("lastSeenChangelogCount") || "0",
      10
    );
    return Math.max(0, CHANGELOG_TOTAL_ITEMS - lastSeenCount);
  });
  const mounted = useSyncExternalStore(
    emptySubscribe,
    getClientSnapshot,
    getServerSnapshot
  );

  // Shopping list badge
  const { data: shoppingData } = useShoppingList();
  const refreshShoppingList = useRefreshShoppingList();

  const shoppingListRemaining = shoppingData
    ? shoppingData.total_items - shoppingData.checked_items
    : 0;

  // Planner update handler
  const handlePlannerUpdated = useCallback(() => {
    try {
      refreshShoppingList();
    } catch (error) {
      console.error("[TopNav] Failed to refresh shopping count:", error);
    }
  }, [refreshShoppingList]);

  // Event listeners
  useEffect(() => {
    window.addEventListener("shopping-list-updated", refreshShoppingList);
    window.addEventListener("planner-updated", handlePlannerUpdated);
    return () => {
      window.removeEventListener("shopping-list-updated", refreshShoppingList);
      window.removeEventListener("planner-updated", handlePlannerUpdated);
    };
  }, [refreshShoppingList, handlePlannerUpdated]);

  // Derived values
  const hasNewUpdates = mounted && changelogNewItems > 0 && !changelogBadgeDismissed;
  const newItemCount = changelogCountReset ? 0 : changelogNewItems;

  const handleChangelogOpenChange = (open: boolean) => {
    if (open) {
      localStorage.setItem("lastSeenChangelogCount", String(CHANGELOG_TOTAL_ITEMS));
      setChangelogBadgeDismissed(true);
    } else {
      setChangelogCountReset(true);
      setChangelogScrollTo(null);
    }
    setChangelogOpen(open);
  };

  const handleSheetNavigate = () => {
    setSheetOpen(false);
  };

  return (
    <>
      {/* Fixed top navigation bar — hidden on mobile, visible on md+ */}
      <header
        className={cn(
          "hidden md:flex",
          "fixed top-0 left-0 right-0 z-30 h-16",
          "items-center gap-2 px-4 lg:px-6",
          "bg-background/95 backdrop-blur-sm border-b border-border",
          "print:hidden"
        )}
      >
        {/* Left section: Logo + App Name + Hamburger */}
        <div className="flex items-center gap-3 mr-6">
          <Logo className="h-8 w-auto flex-shrink-0" />
          <span className="text-lg font-semibold text-foreground whitespace-nowrap">
            {appConfig.appName}
          </span>

          {/* Hamburger button — visible between md and lg */}
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden ml-1"
            aria-label="Open navigation menu"
            onClick={() => setSheetOpen(true)}
          >
            <Menu className="size-5" strokeWidth={1.5} />
          </Button>
        </div>

        {/* Center section: Inline nav links — hidden below lg */}
        <nav className="hidden lg:flex items-center gap-1.5 flex-1" aria-label="Main navigation">
          {navigation.map((item) => (
            <TopNavLink
              key={item.href}
              icon={item.icon}
              label={item.name}
              href={item.href}
              isActive={pathname === item.href}
              badge={item.hasBadge ? shoppingListRemaining : undefined}
            />
          ))}
          <TopNavAddMenu />
        </nav>

        {/* Spacer to push right section when nav is hidden */}
        <div className="flex-1 lg:hidden" />

        {/* Pinned page actions — injected from PageLayout when header scrolls out */}
        {navActions && (
          <div
            className={cn(
              "flex items-center gap-2 border-l border-border pl-3",
              "transition-all duration-200",
              isPinned
                ? "opacity-100 translate-y-0"
                : "opacity-0 -translate-y-2 pointer-events-none"
            )}
          >
            {navActions}
          </div>
        )}

        {/* Right section: Assistant, Theme toggle, Changelog, Avatar */}
        <div className="flex items-center gap-2.5 border-l border-border pl-3">
          {/* Genie assistant trigger */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Open the Genie"
                onClick={onOpenAssistant}
              >
                <Sparkles className="size-5" strokeWidth={1.5} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Genie</TooltipContent>
          </Tooltip>

          {/* Theme toggle — single icon */}
          {mounted && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
                  onClick={toggleTheme}
                >
                  {resolvedTheme === "dark" ? (
                    <Sun className="size-5" strokeWidth={1.5} />
                  ) : (
                    <Moon className="size-5" strokeWidth={1.5} />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {resolvedTheme === "dark" ? "Light mode" : "Dark mode"}
              </TooltipContent>
            </Tooltip>
          )}

          {/* Changelog / What's New */}
          <ChangelogPopover
            newItemCount={newItemCount}
            hasNewUpdates={hasNewUpdates}
            onOpen={() => {
              localStorage.setItem("lastSeenChangelogCount", String(CHANGELOG_TOTAL_ITEMS));
              setChangelogBadgeDismissed(true);
            }}
            onViewAll={() => handleChangelogOpenChange(true)}
            onViewItem={(globalIndex) => {
              setChangelogScrollTo(globalIndex);
              handleChangelogOpenChange(true);
            }}
          />

          {/* User avatar dropdown */}
          <TopNavUserMenu
            onOpenAssistant={onOpenAssistant}
            onOpenFeedback={() => setFeedbackOpen(true)}
          />
        </div>
      </header>

      {/* Spacer to push content below the fixed nav bar */}
      <div className="hidden md:block h-16 print:hidden" aria-hidden="true" />

      {/* Hamburger Sheet — slides in from left for md-to-lg widths */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetHeader className="px-4 pt-6 pb-2">
            <SheetTitle className="flex items-center gap-3">
              <Logo className="h-8 w-auto" />
              {appConfig.appName}
            </SheetTitle>
          </SheetHeader>
          <nav className="p-3 space-y-1" aria-label="Navigation menu">
            {navigation.map((item) => (
              <NavButton
                key={item.href}
                icon={item.icon}
                label={item.name}
                href={item.href}
                isActive={pathname === item.href}
                badge={item.hasBadge ? shoppingListRemaining : undefined}
                onClick={handleSheetNavigate}
              />
            ))}

            {/* Add actions */}
            <div className="h-px bg-border my-2" />
            <Button
              variant="ghost"
              onClick={() => {
                setSheetOpen(false);
                openWizard();
              }}
              className={cn(
                "flex items-center justify-start gap-3 px-3 py-3 h-auto rounded-xl w-full",
                "transition-all duration-200 ease-physical",
                "text-muted-foreground hover:text-foreground",
                "hover:bg-hover/70",
                "hover:translate-x-1",
                "active:scale-[0.98]"
              )}
            >
              <div className="relative p-2 rounded-lg transition-colors duration-200 group-hover:bg-hover/50">
                <Plus className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <span className="text-sm font-medium">Add Recipe</span>
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setSheetOpen(false);
                router.push("/meal-planner?addMeal=1");
              }}
              className={cn(
                "flex items-center justify-start gap-3 px-3 py-3 h-auto rounded-xl w-full",
                "transition-all duration-200 ease-physical",
                "text-muted-foreground hover:text-foreground",
                "hover:bg-hover/70",
                "hover:translate-x-1",
                "active:scale-[0.98]"
              )}
            >
              <div className="relative p-2 rounded-lg transition-colors duration-200 group-hover:bg-hover/50">
                <UtensilsCrossed className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <span className="text-sm font-medium">Add Meal</span>
            </Button>
          </nav>
        </SheetContent>
      </Sheet>

      {/* Dialogs */}
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />
      <ChangelogDialog
        open={changelogOpen}
        onOpenChange={handleChangelogOpenChange}
        newItemCount={newItemCount}
        scrollToItem={changelogScrollTo}
      />
    </>
  );
}
