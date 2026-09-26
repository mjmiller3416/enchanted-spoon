import { ErrorReportingUser } from "@/components/common/ErrorReportingUser";
import { AppLayout } from "@/components/layout/AppLayout";

export default function AppGroupLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <AppLayout>
      <ErrorReportingUser />
      {children}
    </AppLayout>
  );
}
