// ⚠️ PLACEHOLDER LEGAL COPY — owner must review with counsel before public launch.
import type { Metadata } from "next";
import { appConfig } from "@/lib/config";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: `How ${appConfig.appName} collects, uses, and protects your data.`,
};

const LAST_UPDATED = "July 13, 2026";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-section-header">{title}</h2>
      {children}
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-16 lg:px-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-page-title">Privacy Policy</h1>
        <p className="text-sm text-muted-foreground">Last updated: {LAST_UPDATED}</p>
      </header>

      <p className="leading-7 text-foreground-subtle">
        {appConfig.appName} (&ldquo;we,&rdquo; &ldquo;us&rdquo;) is a recipe management and
        meal planning application. This policy describes what information we collect when
        you use the service, how we use it, and the choices you have.
      </p>

      <Section title="Information we collect">
        <ul className="flex list-disc flex-col gap-2 pl-6 leading-7 text-foreground-subtle">
          <li>
            <strong className="text-foreground">Account information.</strong> Sign-up and
            sign-in are handled by Clerk, our authentication provider. We receive your name,
            email address, and profile image from Clerk to create and maintain your account.
          </li>
          <li>
            <strong className="text-foreground">Content you create.</strong> Recipes,
            ingredients, meal plans, shopping lists, cooking history, settings, and feedback
            you submit are stored in our database so the service can function.
          </li>
          <li>
            <strong className="text-foreground">Images.</strong> Recipe photos you upload or
            generate are hosted by Cloudinary, our image hosting provider.
          </li>
          <li>
            <strong className="text-foreground">AI feature inputs.</strong> When you use AI
            features (recipe generation, URL import, the Genie assistant, cooking tips,
            nutrition estimation, image generation), the prompts and relevant recipe context
            are processed by Google Gemini to produce results. We also track your usage counts
            of these features.
          </li>
        </ul>
      </Section>

      <Section title="Cookies and local storage">
        <p className="leading-7 text-foreground-subtle">
          We use cookies for authentication (via Clerk) and your browser&apos;s local storage
          for preferences such as theme, chat history, recently viewed recipes, and filter
          state. We do not use third-party advertising or tracking cookies.
        </p>
      </Section>

      <Section title="How we use your information">
        <p className="leading-7 text-foreground-subtle">
          We use your information solely to provide and improve the service: keeping your
          recipes and plans in sync, building your shopping list, powering AI features you
          invoke, and responding to feedback. We do not sell your personal information.
        </p>
      </Section>

      <Section title="Data export and deletion">
        <p className="leading-7 text-foreground-subtle">
          You can export a complete backup of your data (recipes, meals, planner entries,
          shopping lists, and settings) or delete your data at any time from Settings &rarr;
          Data Management inside the app. Deleting your account removes your content from our
          systems.
        </p>
      </Section>

      <Section title="Third-party services">
        <p className="leading-7 text-foreground-subtle">
          We rely on the following processors to run the service: Clerk (authentication),
          Cloudinary (image hosting), Google Gemini (AI processing), and Railway (hosting).
          Each processes only the data needed for its role, under its own privacy terms.
        </p>
      </Section>

      <Section title="Changes to this policy">
        <p className="leading-7 text-foreground-subtle">
          We may update this policy as the service evolves. Material changes will be noted on
          this page with a new &ldquo;last updated&rdquo; date.
        </p>
      </Section>

      <Section title="Contact">
        <p className="leading-7 text-foreground-subtle">
          Questions about this policy or your data? Email{" "}
          <a href={`mailto:${appConfig.supportEmail}`} className="text-primary hover:underline">
            {appConfig.supportEmail}
          </a>
          .
        </p>
      </Section>
    </article>
  );
}
