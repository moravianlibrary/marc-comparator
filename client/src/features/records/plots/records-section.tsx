import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FacetChart } from "./facet-chart";
import { BarFacet } from "./bar-facet";
import { DonutFacet } from "./donut-facet";
import { StatusTripleFacet } from "./status-triple-facet";
import type { FacetBucket } from "../types";
import type { ChartId } from "./use-section-visibility";

interface RecordsSectionProps {
  isVisible: (chart: ChartId) => boolean;
  getBuckets: (field: string) => FacetBucket[];
  getActiveValues: (field: string) => string[];
  getPreviewBuckets: (field: string) => FacetBucket[] | undefined;
  makeChartHandlers: (field: string) => {
    onToggle: (value: string) => void;
    onHover: (value: string) => void;
    onLeave: () => void;
  };
  handleToggle: (facetField: string, value: string) => void;
  prefetch: (field: string) => void;
  setHoveredField: (field: string | null) => void;
  setHoveredValue: (value: string | null) => void;
}

export function RecordsSection({
  isVisible,
  getBuckets,
  getActiveValues,
  getPreviewBuckets,
  makeChartHandlers,
  handleToggle,
  prefetch,
  setHoveredField,
  setHoveredValue,
}: RecordsSectionProps) {
  const { t } = useTranslation("records");

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        {t("plots.sections.records")}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {isVisible("record_status") && (
          <Card
            className={cn(
              "xl:col-span-1",
              (getActiveValues("is_deleted").length > 0 ||
                getActiveValues("review_status").length > 0 ||
                getActiveValues("is_processed").length > 0) &&
                "ring-2 ring-primary/30",
            )}
            onMouseEnter={() => {
              prefetch("is_deleted");
              prefetch("review_status");
              prefetch("is_processed");
            }}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                {t("plots.record-status")}
                {(getActiveValues("is_deleted").length > 0 ||
                  getActiveValues("review_status").length > 0 ||
                  getActiveValues("is_processed").length > 0) && (
                  <span className="inline-block h-2 w-2 rounded-full bg-primary" />
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <StatusTripleFacet
                rows={[
                  {
                    label: t("facet-fields.is_deleted"),
                    facetField: "is_deleted",
                    buckets: getBuckets("is_deleted"),
                    previewBuckets: getPreviewBuckets("is_deleted"),
                    segments: [
                      { key: "Active", color: "var(--chart-1)" },
                      { key: "Deleted", color: "var(--chart-4)" },
                    ],
                  },
                  {
                    label: t("facet-fields.is_processed"),
                    facetField: "is_processed",
                    buckets: getBuckets("is_processed"),
                    previewBuckets: getPreviewBuckets("is_processed"),
                    segments: [
                      { key: "Processed", color: "var(--chart-1)" },
                      { key: "Unprocessed", color: "var(--chart-4)" },
                    ],
                  },
                  {
                    label: t("facet-fields.review_status"),
                    facetField: "review_status",
                    buckets: getBuckets("review_status"),
                    previewBuckets: getPreviewBuckets("review_status"),
                    segments: [
                      { key: "Reviewed", color: "var(--chart-1)" },
                      { key: "PartiallyReviewed", color: "var(--chart-3)" },
                      { key: "Unreviewed", color: "var(--chart-4)" },
                      { key: "ReviewNotNeeded", color: "var(--chart-5)" },
                    ],
                  },
                ]}
                activeValues={{
                  is_deleted: getActiveValues("is_deleted"),
                  is_processed: getActiveValues("is_processed"),
                  review_status: getActiveValues("review_status"),
                }}
                onToggle={handleToggle}
                onHover={(field, value) => {
                  if (getActiveValues(field).includes(value)) return;
                  setHoveredField(field);
                  setHoveredValue(value);
                }}
                onLeave={() => {
                  setHoveredField(null);
                  setHoveredValue(null);
                }}
              />
            </CardContent>
          </Card>
        )}

        {isVisible("type_of_record") &&
          getBuckets("type_of_record").length > 0 && (
            <FacetChart
              title={t("facet-fields.type_of_record")}
              facetField="type_of_record"
              className="md:order-3 md:col-span-2 xl:order-none xl:col-span-1"
              data={getBuckets("type_of_record")}
              previewData={getPreviewBuckets("type_of_record")}
              activeValues={getActiveValues("type_of_record")}
              formatLabel={(k) => t(`type-of-record.${k}`, { defaultValue: k })}
              {...makeChartHandlers("type_of_record")}
            >
              {(chartProps) => <BarFacet {...chartProps} labelWidth={240} />}
            </FacetChart>
          )}

        {isVisible("bibliographic_level") &&
          getBuckets("bibliographic_level").length > 0 && (
            <FacetChart
              title={t("facet-fields.bibliographic_level")}
              facetField="bibliographic_level"
              className="md:order-2 xl:order-none"
              data={getBuckets("bibliographic_level")}
              previewData={getPreviewBuckets("bibliographic_level")}
              activeValues={getActiveValues("bibliographic_level")}
              formatLabel={(k) => t(`bibliographic-level.${k}`, { defaultValue: k })}
              contentClassName="flex justify-center"
              {...makeChartHandlers("bibliographic_level")}
            >
              {(chartProps) => <DonutFacet {...chartProps} />}
            </FacetChart>
          )}
      </div>
    </section>
  );
}
