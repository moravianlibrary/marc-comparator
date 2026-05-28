import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { ContextPills } from "./context-pills";
import type { FacetBucket } from "../types";

export interface PillGroup {
  label: string;
  facetField: string;
  buckets: FacetBucket[];
  previewBuckets?: FacetBucket[];
  activeValues: string[];
  formatLabel?: (k: string) => string;
  onToggle: (value: string) => void;
  onHover: (value: string) => void;
  onLeave: () => void;
}

interface ContextSectionProps {
  pillGroups: PillGroup[];
  hasRecordIdFilter: boolean;
  recordId: string;
  onClearRecordId: () => void;
}

export function ContextSection({
  pillGroups,
  hasRecordIdFilter,
  recordId,
  onClearRecordId,
}: ContextSectionProps) {
  const { t } = useTranslation("records");

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        {t("plots.sections.context")}
      </h3>
      <Card>
        <CardContent className="flex flex-wrap gap-x-6 gap-y-3 pt-4">
          {hasRecordIdFilter && (
            <div>
              <p className="text-sm font-medium mb-1">{t("plots.record-id")}</p>
              <button
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-sm font-medium bg-primary text-primary-foreground"
                onClick={onClearRecordId}
              >
                <span>{recordId}</span>
                <X className="h-3 w-3" />
              </button>
            </div>
          )}
          {pillGroups.map((group) => (
            <div key={group.facetField}>
              <p className="text-sm font-medium mb-1">{group.label}</p>
              <ContextPills
                buckets={group.buckets}
                previewBuckets={group.previewBuckets}
                activeValues={group.activeValues}
                onToggle={group.onToggle}
                onHover={group.onHover}
                onLeave={group.onLeave}
                formatLabel={group.formatLabel}
              />
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  );
}
