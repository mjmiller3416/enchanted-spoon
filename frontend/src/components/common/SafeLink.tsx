"use client";

import { useCallback, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { hasAnyUnsavedChanges, discardUnsavedChanges, setNavigationBypass } from "@/hooks/ui/useUnsavedChanges";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AlertTriangle } from "lucide-react";

interface SafeLinkProps {
  "aria-current"?: React.AriaAttributes["aria-current"];
  href: string;
  children: React.ReactNode;
  className?: string;
  onClick?: (e: React.MouseEvent) => void;
}

/**
 * A Link component that checks for unsaved changes before navigating.
 * If any page has registered unsaved changes, shows a confirmation dialog.
 * 
 * Use this in navigation components (like Sidebar) to respect unsaved changes.
 */
export function SafeLink({ href, children, className, onClick, ...ariaProps }: SafeLinkProps) {
  const router = useRouter();
  const [showDialog, setShowDialog] = useState(false);
  // Use ref to store href so it's not affected by state updates during dialog close
  const pendingHrefRef = useRef<string | null>(null);
  // Track if we're in the middle of confirming to prevent onOpenChange interference
  const isConfirmingRef = useRef(false);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      // Call the original onClick if provided
      onClick?.(e);
      
      // If already prevented, don't do anything
      if (e.defaultPrevented) return;

      // Check for unsaved changes
      if (hasAnyUnsavedChanges()) {
        e.preventDefault();
        pendingHrefRef.current = href;
        setShowDialog(true);
      }
      // Otherwise, let the Link handle navigation normally
    },
    [href, onClick]
  );

  const handleConfirm = useCallback(() => {
    // Mark that we're confirming to prevent onOpenChange from interfering
    isConfirmingRef.current = true;
    
    // Enable bypass to prevent re-interception
    discardUnsavedChanges();
    setNavigationBypass(true);
    
    // Get the href before any state changes
    const targetHref = pendingHrefRef.current;
    
    // Close dialog
    setShowDialog(false);
    
    // Navigate after a micro-delay to ensure state updates have settled
    if (targetHref) {
      // Use setTimeout to ensure this runs after React's state updates
      setTimeout(() => {
        router.push(targetHref);
        pendingHrefRef.current = null;
        isConfirmingRef.current = false;
      }, 0);
    }
  }, [router]);

  const handleCancel = useCallback(() => {
    setShowDialog(false);
    pendingHrefRef.current = null;
  }, []);

  const handleOpenChange = useCallback((open: boolean) => {
    // Don't interfere if we're in the middle of confirming
    if (isConfirmingRef.current) return;
    
    // Only allow closing (not opening) through onOpenChange
    if (!open) {
      setShowDialog(false);
      pendingHrefRef.current = null;
    }
  }, []);

  return (
    <>
      <Link {...ariaProps} href={href} className={className} onClick={handleClick}>
        {children}
      </Link>

      <AlertDialog open={showDialog} onOpenChange={handleOpenChange}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-secondary" strokeWidth={1.5} />
              Unsaved Changes
            </AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Are you sure you want to leave this page? Your changes will be lost.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancel}>Keep Editing</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Discard Changes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}