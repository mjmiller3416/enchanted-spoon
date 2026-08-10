// ⚠️ PLACEHOLDER LEGAL COPY — owner must review with counsel before public launch.
import type { Metadata } from "next";
import { appConfig } from "@/lib/config";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "The terms that govern your use of Whiskful.",
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

export default function TermsPage() {
  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-16 lg:px-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-page-title">Terms of Service</h1>
        <p className="text-sm text-muted-foreground">Last updated: {LAST_UPDATED}</p>
      </header>

      <p className="leading-7 text-foreground-subtle">
        These terms govern your use of {appConfig.appName}, a recipe management and meal
        planning application. By creating an account or using the service, you agree to them.
      </p>

      <Section title="Your account">
        <p className="leading-7 text-foreground-subtle">
          You must provide accurate information when creating an account and keep your
          credentials secure. You are responsible for activity that happens under your
          account. Authentication is provided by Clerk.
        </p>
      </Section>

      <Section title="Your content">
        <p className="leading-7 text-foreground-subtle">
          You own the recipes, images, meal plans, and other content you add to the service.
          By uploading content, you grant us the limited license needed to store, display, and
          process it for you — including hosting images with Cloudinary and sending relevant
          context to Google Gemini when you use AI features. You are responsible for making
          sure content you import or upload doesn&apos;t infringe anyone else&apos;s rights.
        </p>
      </Section>

      <Section title="AI-generated content">
        <p className="leading-7 text-foreground-subtle">
          AI features (recipe generation, URL import, the assistant, cooking tips, nutrition
          estimation, and image generation) produce automated output that may be inaccurate or
          incomplete. Nutrition estimates are informational only and are not medical or dietary
          advice — always verify ingredients and allergens yourself. AI usage may be subject to
          reasonable limits.
        </p>
      </Section>

      <Section title="Acceptable use">
        <p className="leading-7 text-foreground-subtle">
          Don&apos;t misuse the service: no attempting to break or overload it, no scraping
          other users&apos; data, no uploading unlawful content, and no reselling access
          without our permission.
        </p>
      </Section>

      <Section title="Data portability and termination">
        <p className="leading-7 text-foreground-subtle">
          You can export a full backup of your data or delete it at any time from Settings
          &rarr; Data Management. You may stop using the service whenever you like. We may
          suspend or terminate accounts that violate these terms.
        </p>
      </Section>

      <Section title="Disclaimers and liability">
        <p className="leading-7 text-foreground-subtle">
          The service is provided &ldquo;as is&rdquo; without warranties of any kind. To the
          maximum extent permitted by law, we are not liable for indirect or consequential
          damages arising from your use of the service.
        </p>
      </Section>

      <Section title="Changes to these terms">
        <p className="leading-7 text-foreground-subtle">
          We may update these terms as the service evolves. Material changes will be noted on
          this page with a new &ldquo;last updated&rdquo; date. Continued use after changes
          means you accept the updated terms.
        </p>
      </Section>

      <Section title="Contact">
        <p className="leading-7 text-foreground-subtle">
          Questions about these terms? Email{" "}
          <a href={`mailto:${appConfig.supportEmail}`} className="text-primary hover:underline">
            {appConfig.supportEmail}
          </a>
          .
        </p>
      </Section>
    </article>
  );
}
