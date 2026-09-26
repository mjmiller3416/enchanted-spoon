"use client";

import * as React from "react";
import { useRef, useEffect } from "react";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  PageHeader,
  PageHeaderContent,
  PageHeaderTitle,
  PageHeaderActions,
} from "./PageHeader";
import { useNavActions } from "@/lib/providers/NavActionsProvider";

interface PageLayoutProps {
  /** Optional page title displayed in the header */
  title?: string;
  /** Optional description displayed below the title */
  description?: string;
  /** Optional actions (buttons, etc.) displayed on the right side of the header */
  actions?: React.ReactNode;
  /** Optional custom header content that completely replaces the default title/actions layout */
  headerContent?: React.ReactNode;
  /** Optional callback when back button is clicked (for custom navigation with unsaved changes) */
  onBackClick?: () => void;
  /** Page content */
  children: React.ReactNode;
  /** Optional className for the outer wrapper */
  className?: string;
  /** Optional className for the content container */
  contentClassName?: string;
  /** Optional hero section that replaces the standard header */
  hero?: React.ReactNode;
  /** Optional sticky header bar below the hero (for sort options, active filters, etc.) */
  stickyHeader?: React.ReactNode;
  /** When true, page fills viewport height exactly with no scrolling (content must manage its own overflow) */
  fillViewport?: boolean;
  /** When true, action buttons pin into the TopNav bar when the header scrolls out of view (desktop only) */
  pinActionsToNav?: boolean;
  /** When true, header and content drop the max-w-7xl cap at lg+ (horizontal padding is kept) */
  fullWidth?: boolean;
}

/**
 * PageLayout - Standard page layout wrapper
 *
 * Supports three modes:
 * 1. Standard with title (default) - Page scrolls normally with title/description header
 * 2. Standard with custom header - Pass headerContent to override default header
 * 3. Hero mode - Hero section at top, sticky subheader for filters/sort
 *
 * For sticky sidebars, use CSS `position: sticky` on child elements.
 * Pass `fullWidth` to let the standard modes span their container at lg+
 * (used by the Menu page, which docks a detail pane beside the layout).
 *
 * @example
 * // Standard page with title, description, and actions
 * <PageLayout
 *   title="Shopping List"
 *   description="Automatically generated from your meal plan."
 *   actions={<Button>Clear All</Button>}
 * >
 *   {content}
 * </PageLayout>
 *
 * @example
 * // Page with custom header (overrides title/description)
 * <PageLayout
 *   headerContent={
 *     <PageHeaderContent>
 *       <CustomHeaderContent />
 *     </PageHeaderContent>
 *   }
 * >
 *   {content}
 * </PageLayout>
 *
 * @example
 * // Hero mode (RecipeBrowser)
 * <PageLayout
 *   hero={<HeroSection />}
 *   stickyHeader={<SortAndFilters />}
 * >
 *   {content}
 * </PageLayout>
 */
export function PageLayout(props: PageLayoutProps) {
  const {
    title,
    description,
    actions,
    headerContent,
    onBackClick,
    children,
    className,
    contentClassName,
    hero,
    stickyHeader,
    fillViewport = false,
    pinActionsToNav = false,
    fullWidth = false,
  } = props;

  const headerRef = useRef<HTMLDivElement>(null);
  const { setNavActions, setPinned, clearNavActions } = useNavActions();

  // Register actions with nav context when pinActionsToNav is enabled
  useEffect(() => {
    if (!pinActionsToNav || !actions) return;
    setNavActions(actions);
    return () => clearNavActions();
  }, [pinActionsToNav, actions, setNavActions, clearNavActions]);

  // Observe header visibility to toggle pinned state
  useEffect(() => {
    if (!pinActionsToNav || !actions || !headerRef.current) return;

    const observer = new IntersectionObserver(
      ([entry]) => setPinned(!entry.isIntersecting),
      {
        // Offset by TopNav height (h-16 = 64px) so pinning triggers
        // when the header scrolls behind the fixed nav bar
        rootMargin: "-64px 0px 0px 0px",
        threshold: 0,
      }
    );

    observer.observe(headerRef.current);
    return () => observer.disconnect();
  }, [pinActionsToNav, actions, setPinned]);

  // Build the header content (shared across modes)
  // Priority: headerContent > (title + actions) > actions only > back button only
  const hasHeader = !!(headerContent || title || actions || onBackClick);
  const headerElement = hasHeader ? (
    <div ref={pinActionsToNav ? headerRef : undefined}>
      <PageHeader fullWidth={fullWidth}>
        {headerContent ? (
          headerContent
        ) : (
          <PageHeaderContent>
            {onBackClick && (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Go back"
                onClick={onBackClick}
              >
                <ArrowLeft className="size-4" strokeWidth={1.5} />
              </Button>
            )}
            {title && <PageHeaderTitle title={title} description={description} />}
            {actions && <PageHeaderActions>{actions}</PageHeaderActions>}
          </PageHeaderContent>
        )}
      </PageHeader>
    </div>
  ) : null;

  // ============================================
  // HERO MODE: Hero section with sticky subheader
  // Used by: RecipeBrowser
  // ============================================
  if (hero) {
    return (
      <div className={cn("min-h-0 bg-background", className)}>
        {/* Hero section */}
        {hero}

        {/* Sticky header bar (sort options, active filters) */}
        {stickyHeader && (
          <div
            data-sticky-header
            className="sticky top-0 md:top-16 z-40 border-b bg-background border-border"
          >
            {stickyHeader}
          </div>
        )}

        {/* Main content area */}
        <div
          data-page-content
          className={cn("max-w-7xl mx-auto w-full px-4 md:px-6 py-6", contentClassName)}
        >
          {children}
        </div>
      </div>
    );
  }

  // ============================================
  // STANDARD MODE: Normal scrolling page
  // Used by: Settings, Add Recipe, Edit Recipe, Shopping List, Meal Planner
  // ============================================

  // fillViewport mode: fixed height, no page scroll, content fills available space
  // On mobile (< lg), use normal scrolling since there's no sidebar that needs independent scroll
  if (fillViewport) {
    return (
      <div className={cn("page-fill-viewport flex flex-col bg-background", className)}>
        {headerElement}
        <div className={cn("flex-1 lg:min-h-0 max-w-7xl mx-auto w-full px-4 md:px-6 py-6", fullWidth && "lg:max-w-none", contentClassName)}>
          {children}
        </div>
      </div>
    );
  }

  // Default: scrollable page
  return (
    <div className={cn("min-h-0 bg-background", className)}>
      {headerElement}
      <div className={cn("max-w-7xl mx-auto px-4 md:px-6 py-6", fullWidth && "lg:max-w-none", contentClassName)}>
        {children}
      </div>
    </div>
  );
}