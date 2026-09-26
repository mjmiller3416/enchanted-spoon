import { Database } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { SectionHeader } from "../SectionHeader";
import { BackupRestore } from "../data-management/BackupRestore";
import { ExportImport } from "../data-management/ExportImport";
import { DeleteData } from "../data-management/DeleteData";
import { SampleData } from "../data-management/SampleData";

export function DataManagementSection() {
  return (
    <Card>
      <CardContent className="pt-6">
        <SectionHeader
          icon={Database}
          title="Data Management"
          description="Back up all your data or import/export recipes"
        />

        <div className="space-y-6">
          <BackupRestore />
          <Separator />
          <ExportImport />
          <Separator />
          <SampleData />
          <Separator />
          <DeleteData />
        </div>
      </CardContent>
    </Card>
  );
}
