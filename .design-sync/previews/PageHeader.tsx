import {
  Button,
  PageHeader,
  PageHeaderActions,
  PageHeaderContent,
  PageHeaderTitle,
} from "enchanted-spoon";
import { ArrowLeft, Pencil, Plus } from "lucide-react";

// Standard page header: title + primary action, as the Meal Planner page
// composes it via PageLayout.
export const TitleWithActions = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-full max-w-2xl">
    <PageHeader>
      <PageHeaderContent>
        <PageHeaderTitle title="Meal Planner" />
        <PageHeaderActions>
          <Button variant="outline">This Week</Button>
          <Button>
            <Plus className="size-4" strokeWidth={1.5} />
            Add Meal
          </Button>
        </PageHeaderActions>
      </PageHeaderContent>
    </PageHeader>
  </div>
);

// Title with inline description text.
export const TitleWithDescription = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-full max-w-2xl">
    <PageHeader>
      <PageHeaderContent>
        <PageHeaderTitle
          title="Shopping List"
          description="12 items across 4 planned meals"
        />
      </PageHeaderContent>
    </PageHeader>
  </div>
);

// Detail-page header with back button, mirroring PageLayout's onBackClick slot.
export const WithBackButton = () => (
  <div className="bg-background text-foreground p-6 rounded-xl w-full max-w-2xl">
    <PageHeader>
      <PageHeaderContent>
        <Button variant="ghost" size="icon" aria-label="Go back">
          <ArrowLeft className="size-4" strokeWidth={1.5} />
        </Button>
        <PageHeaderTitle title="Bruschetta Shrimp Pasta" />
        <PageHeaderActions>
          <Button variant="outline">
            <Pencil className="size-4" strokeWidth={1.5} />
            Edit Recipe
          </Button>
        </PageHeaderActions>
      </PageHeaderContent>
    </PageHeader>
  </div>
);
