"use client"

import * as React from "react"
import * as AlertDialogPrimitive from "@radix-ui/react-alert-dialog"

import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"
import { registerConfirmDismiss } from "@/lib/confirm-dismiss"

const AlertDialogDismissContext = React.createContext<(() => void) | null>(null)

function AlertDialog({
  open,
  onOpenChange,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Root>) {
  const requestClose = React.useCallback(() => {
    onOpenChange?.(false)
  }, [onOpenChange])

  // Hardware back (see handleNativeBackButton) closes this prompt. Closing
  // is the safe action: callers treat onOpenChange(false) as cancel.
  React.useEffect(() => {
    if (!open) return
    return registerConfirmDismiss(requestClose)
  }, [open, requestClose])

  return (
    <AlertDialogDismissContext.Provider value={requestClose}>
      <AlertDialogPrimitive.Root
        data-slot="alert-dialog"
        open={open}
        onOpenChange={onOpenChange}
        {...props}
      />
    </AlertDialogDismissContext.Provider>
  )
}

function AlertDialogTrigger({
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Trigger>) {
  return (
    <AlertDialogPrimitive.Trigger data-slot="alert-dialog-trigger" {...props} />
  )
}

function AlertDialogPortal({
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Portal>) {
  return (
    <AlertDialogPrimitive.Portal data-slot="alert-dialog-portal" {...props} />
  )
}

function AlertDialogOverlay({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Overlay>) {
  return (
    <AlertDialogPrimitive.Overlay
      data-slot="alert-dialog-overlay"
      className={cn(
        "fixed inset-0 z-[70] bg-black/60",
        // No backdrop-blur: on some Android WebViews the blur layer sits
        // above the dialog and steals taps from the lower button.
        "transition-opacity duration-200 ease-physical",
        "data-[state=open]:animate-in data-[state=closed]:animate-out",
        "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogContent({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Content>) {
  const requestClose = React.useContext(AlertDialogDismissContext)
  return (
    <AlertDialogPortal>
      <AlertDialogOverlay />
      {/* Inset by the safe area and center in the remaining box. A
          translateY(-50%) dialog with no max-height clips the lower button
          on short and landscape phones. Taps on this frame (not the card)
          cancel the prompt. Radix AlertDialog blocks outside presses itself. */}
      <div
        data-slot="alert-dialog-viewport"
        className={cn(
          "fixed inset-0 z-[70] flex items-center justify-center overflow-y-auto",
          "pt-[max(1rem,env(safe-area-inset-top,0px))]",
          "pr-[max(1rem,env(safe-area-inset-right,0px))]",
          "pb-[max(1rem,env(safe-area-inset-bottom,0px))]",
          "pl-[max(1rem,env(safe-area-inset-left,0px))]"
        )}
        onPointerDown={(event) => {
          if (event.target === event.currentTarget) requestClose?.()
        }}
      >
        <AlertDialogPrimitive.Content
          data-slot="alert-dialog-content"
          className={cn(
            "relative flex w-full max-w-lg flex-col gap-4 overflow-y-auto",
            "max-h-[calc(100dvh-env(safe-area-inset-top,0px)-env(safe-area-inset-bottom,0px)-2rem)]",
            "bg-elevated border border-border rounded-xl p-6 pb-0 shadow-xl shadow-black/20",
            "transition-all duration-200 ease-physical outline-none",
            "data-[state=open]:animate-in data-[state=closed]:animate-out",
            "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
            "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95",
            className
          )}
          {...props}
        />
      </div>
    </AlertDialogPortal>
  )
}

function AlertDialogHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-header"
      className={cn("flex flex-col gap-1.5 text-center sm:text-left", className)}
      {...props}
    />
  )
}

function AlertDialogFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-footer"
      className={cn(
        // Always a row (wraps only if the two labels cannot sit together).
        // flex-col-reverse placed Keep editing below Discard, which is the
        // button a short viewport or the system bar covered.
        "sticky bottom-0 z-10 -mx-6 mt-2 flex shrink-0 flex-row flex-wrap items-center gap-2",
        "bg-elevated px-6 pt-2 pb-6 sm:justify-end",
        "[&>*]:w-full [&>*]:flex-1 sm:[&>*]:w-auto sm:[&>*]:flex-none",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogTitle({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Title>) {
  return (
    <AlertDialogPrimitive.Title
      data-slot="alert-dialog-title"
      className={cn("text-lg font-semibold text-foreground", className)}
      {...props}
    />
  )
}

function AlertDialogDescription({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Description>) {
  return (
    <AlertDialogPrimitive.Description
      data-slot="alert-dialog-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

function AlertDialogAction({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Action>) {
  return (
    <AlertDialogPrimitive.Action
      data-slot="alert-dialog-action"
      className={cn(buttonVariants({ variant: "default", size: "default" }), className)}
      {...props}
      type="button"
    />
  )
}

function AlertDialogCancel({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Cancel>) {
  return (
    <AlertDialogPrimitive.Cancel
      data-slot="alert-dialog-cancel"
      className={cn(buttonVariants({ variant: "outline", size: "default" }), className)}
      {...props}
      type="button"
    />
  )
}

export {
  AlertDialog,
  AlertDialogPortal,
  AlertDialogOverlay,
  AlertDialogTrigger,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogAction,
  AlertDialogCancel,
}
