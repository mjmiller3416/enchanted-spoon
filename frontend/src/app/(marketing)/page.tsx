import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { appConfig } from "@/lib/config";
import { CtaBand } from "./_components/CtaBand";
import { Features } from "./_components/Features";
import { Hero } from "./_components/Hero";
import { HowItWorks } from "./_components/HowItWorks";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: appConfig.appName,
  applicationCategory: "LifestyleApplication",
  operatingSystem: "Web",
  description:
    "Keep your recipes in one place, plan the week's dinners, and get a grocery list that builds itself. Free for recipes, meal planning, and grocery lists.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

export default async function RootPage() {
  const { userId } = await auth();
  if (userId) redirect("/dashboard");

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Hero />
      <HowItWorks />
      <Features />
      <CtaBand />
    </>
  );
}
