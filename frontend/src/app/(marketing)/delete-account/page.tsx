import type { Metadata } from "next";
import Link from "next/link";
import { appConfig } from "@/lib/config";

export const metadata: Metadata = {
  title: "Delete your Enchanted Spoon account",
  description: `How to delete your ${appConfig.appName} account, what is removed, and what can remain.`,
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-section-header">{title}</h2>
      {children}
    </section>
  );
}

export default function DeleteAccountPage() {
  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-16 lg:px-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-page-title">Delete your Enchanted Spoon account</h1>
        <p className="text-sm text-muted-foreground">
          This page is public. You do not need to sign in to read it.
        </p>
      </header>

      <p className="leading-7 text-foreground-subtle">
        You can delete your {appConfig.appName} account in the app, or ask us to delete it
        by email. In-app deletion runs when you confirm it. Email requests are completed
        within 30 days.
      </p>

      <Section title="How to delete your account">
        <ol className="flex list-decimal flex-col gap-3 pl-6 leading-7 text-foreground-subtle">
          <li>
            <strong className="text-foreground">In the app.</strong> Open{" "}
            <strong className="text-foreground">Settings</strong>, then{" "}
            <strong className="text-foreground">Account &amp; Profile</strong>, then{" "}
            <strong className="text-foreground">Delete Account</strong>. Type DELETE to
            confirm. If you own a household that still has other members, deletion waits
            until you transfer the household or remove those members. The app tells you
            that before anything is removed. To keep a copy of your recipes, download one
            from <strong className="text-foreground">Settings</strong>, then{" "}
            <strong className="text-foreground">Data Management</strong>, first.
          </li>
          <li>
            <strong className="text-foreground">By email.</strong> Email{" "}
            <a
              href={`mailto:${appConfig.supportEmail}?subject=Delete%20my%20Enchanted%20Spoon%20account`}
              className="text-primary hover:underline"
            >
              {appConfig.supportEmail}
            </a>{" "}
            from the email address on the account and ask for the account to be deleted.
            We complete email requests within 30 days.
          </li>
        </ol>
      </Section>

      <Section title="What data is deleted">
        <p className="leading-7 text-foreground-subtle">
          Deleting the account removes the data the app stores for you:
        </p>
        <ul className="flex list-disc flex-col gap-2 pl-6 leading-7 text-foreground-subtle">
          <li>
            <strong className="text-foreground">Account and profile.</strong> Your name,
            email, and profile image on the account, and the sign-in identity when the
            sign-in provider accepts the deletion.
          </li>
          <li>
            <strong className="text-foreground">Recipes.</strong> Recipes you created,
            including ingredients, directions, notes, nutrition, groups, and cooking
            history. A meal that uses one of your recipes as its main dish is removed
            with that recipe, including a meal on a household menu.
          </li>
          <li>
            <strong className="text-foreground">Meals and menu.</strong> Meals and menu
            entries saved on your account.
          </li>
          <li>
            <strong className="text-foreground">Shopping lists.</strong> Shopping items,
            the recipes that contributed them, and the notes on your list.
          </li>
          <li>
            <strong className="text-foreground">Settings.</strong> Saved settings, custom
            categories and units, unit conversions, AI usage counts, and push-notification
            tokens for the account.
          </li>
          <li>
            <strong className="text-foreground">Household.</strong> Your membership is
            removed. If you are the only member, the household, its invites, and its
            shared-recipe links are deleted too.
          </li>
          <li>
            <strong className="text-foreground">Recipe photos you own.</strong> Photos you
            uploaded or generated are deleted from image hosting when they are stored in
            that recipe&apos;s own image folder.
          </li>
          <li>
            <strong className="text-foreground">Web subscription.</strong> If the account
            has a Stripe customer, that customer is deleted, which cancels the web
            subscription immediately. If billing cannot be cancelled, the account is not
            deleted.
          </li>
        </ul>
      </Section>

      <Section title="What may be retained">
        <p className="leading-7 text-foreground-subtle">
          These items are not removed by account deletion:
        </p>
        <ul className="flex list-disc flex-col gap-2 pl-6 leading-7 text-foreground-subtle">
          <li>
            <strong className="text-foreground">Store subscriptions.</strong> A Google Play
            or App Store subscription is not cancelled when the {appConfig.appName}{" "}
            account is deleted. Cancel it in the store&apos;s subscription settings. The
            copy of that subscription stored on the account is removed with the account.
          </li>
          <li>
            <strong className="text-foreground">Some recipe photos.</strong> If an image
            delete fails, that file can remain on the image host. A photo a recipe only
            references and does not own, such as starter-recipe artwork, is not deleted.
          </li>
          <li>
            <strong className="text-foreground">Sign-in, if removal fails.</strong> If the
            sign-in provider cannot be reached, the sign-in can remain after the app data
            is gone. Signing in again starts a new, empty account.
          </li>
          <li>
            <strong className="text-foreground">Feedback you already sent.</strong>{" "}
            Feedback is stored as a support request and is not removed with the account.
            Email{" "}
            <a href={`mailto:${appConfig.supportEmail}`} className="text-primary hover:underline">
              {appConfig.supportEmail}
            </a>{" "}
            if you want that request reviewed or removed.
          </li>
          <li>
            <strong className="text-foreground">Someone else&apos;s household invite.</strong>{" "}
            An invite another person created can keep an email address that was used to
            limit who may join. That invite belongs to their household.
          </li>
          <li>
            <strong className="text-foreground">Data on your device.</strong> Preferences
            saved only in this browser, such as theme and chat history, stay on the device
            until you clear them. A backup you already downloaded stays in your files.
          </li>
        </ul>
      </Section>

      <Section title="Contact">
        <p className="leading-7 text-foreground-subtle">
          Questions about deleting your account? Email{" "}
          <a href={`mailto:${appConfig.supportEmail}`} className="text-primary hover:underline">
            {appConfig.supportEmail}
          </a>
          . The{" "}
          <Link href="/privacy" className="text-primary hover:underline">
            privacy policy
          </Link>{" "}
          describes how the service handles data more broadly.
        </p>
      </Section>
    </article>
  );
}
