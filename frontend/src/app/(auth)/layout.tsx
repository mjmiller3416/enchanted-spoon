import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { AuthScreen } from "@/components/auth/AuthScreen";

export default async function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { userId } = await auth();
  if (userId) redirect("/dashboard");
  return <AuthScreen>{children}</AuthScreen>;
}
