import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { appConfig } from "@/lib/config";
import { Benefits } from "./_components/Benefits";
import { CtaBand } from "./_components/CtaBand";
import { ExampleWeek } from "./_components/ExampleWeek";
import { Hero } from "./_components/Hero";
import { HowItWorks } from "./_components/HowItWorks";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: appConfig.appName,
  applicationCategory: "LifestyleApplication",
  operatingSystem: "Web",
  description:
    "Save the recipes you cook, plan the week, and shop from one list. Free for recipes, meal planning, and shopping lists.",
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
      <ExampleWeek />
      <Benefits />
      <CtaBand />
    </>
  );
}
