import * as React from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export function PageHeader({ children, className }: PageHeaderProps) {
  return (
    <div className={cn("bg-background", className)}>
      <div className="pt-6 lg:pt-8 px-4 mx-auto max-w-7xl md:px-6">
        {children}
      </div>
    </div>
  );
}

interface PageHeaderContentProps {
  children: React.ReactNode;
  className?: string;
}

export function PageHeaderContent({ children, className }: PageHeaderContentProps) {
  return (
    <div className={cn("flex flex-wrap items-start gap-x-6 gap-y-4 sm:items-center", className)}>
      {children}
    </div>
  );
}

interface PageHeaderTitleProps {
  title: string;
  description?: string;
  className?: string;
}

export function PageHeaderTitle({ title, description, className }: PageHeaderTitleProps) {
  if (description) {
    return (
      <div className={cn("flex min-w-0 flex-1 basis-56 flex-col gap-2", className)}>
        <h1 className="text-page-title text-balance">
          {title}
        </h1>
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          {description}
        </p>
      </div>
    );
  }

  return (
    <h1 className={cn("min-w-0 flex-1 basis-56 text-page-title text-balance", className)}>
      {title}
    </h1>
  );
}

interface PageHeaderActionsProps {
  children: React.ReactNode;
  className?: string;
}

export function PageHeaderActions({ children, className }: PageHeaderActionsProps) {
  return (
    <div className={cn("flex w-full flex-wrap items-center gap-2 sm:ml-auto sm:w-auto", className)}>
      {children}
    </div>
  );
}
