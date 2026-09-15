"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Shield, Database, Activity } from "lucide-react";
import { SectionNav } from "@/components/layout/SectionNav";
import { QueryError } from "@/components/common/QueryError";
import { PageLayout } from "@/components/layout/PageLayout";
import { SidebarPageSkeleton } from "@/components/layout/SidebarPageSkeleton";
import { useCurrentUser } from "@/hooks/api";
import { AdminUsersSection } from "./AdminUsersSection";
import { AdminUsageSection } from "./AdminUsageSection";
import { AdminDatabaseSection } from "./AdminDatabaseSection";

type AdminTab = "users" | "usage" | "database";

interface TabConfig {
  id: AdminTab;
  label: string;
  icon: React.ElementType;
  description: string;
}

const TABS: TabConfig[] = [
  {
    id: "users",
    label: "User Management",
    icon: Shield,
    description: "Manage users and access levels",
  },
  {
    id: "usage",
    label: "AI Usage",
    icon: Activity,
    description: "AI usage and limits by user",
  },
  {
    id: "database",
    label: "Database Query",
    icon: Database,
    description: "Run read-only SQL queries",
  },
];

export function AdminView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = TABS.find(tab => tab.id === searchParams.get("section"))?.id ?? "users";
  const setActiveTab = (tab: AdminTab) => router.push(`/admin?section=${tab}`, { scroll: false });
  const { isAdmin, isLoading, error, refetch, isFetching } = useCurrentUser();

  // Show loading state (skeleton matches the final sidebar+content layout)
  if (isLoading) {
    return <SidebarPageSkeleton />;
  }

  if (error) return <PageLayout title="Admin Panel"><QueryError title="Couldn’t verify admin access" onRetry={() => void refetch()} retrying={isFetching} /></PageLayout>;

  // Block non-admin users
  if (!isAdmin) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center">
          <Shield className="h-12 w-12 text-muted-foreground" strokeWidth={1.5} />
          <h2 className="text-lg font-semibold text-foreground">Access Denied</h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            You don&apos;t have admin privileges to access this page.
          </p>
        </div>
      </div>
    );
  }

  const renderContent = () => {
    switch (activeTab) {
      case "users":
        return <AdminUsersSection />;
      case "usage":
        return <AdminUsageSection />;
      case "database":
        return <AdminDatabaseSection />;
      default:
        return null;
    }
  };

  return (
    <PageLayout
      title="Admin Panel"
      description="Manage users and access levels."
    >
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 lg:gap-8">
        {/* Left Sidebar - Tab Navigation */}
        <div className="lg:col-span-1">
          <div className="sticky top-24">
            <SectionNav sections={TABS} active={activeTab} onChange={setActiveTab} label="Admin section" />
          </div>
        </div>

        {/* Right Content */}
        <div className="min-w-0 lg:col-span-3 space-y-6">{renderContent()}</div>
      </div>
    </PageLayout>
  );
}
