import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useRecordFilters } from "../use-record-filters";
import { useFacets, usePreviewForValue } from "./use-facets";
import { FacetChart } from "./facet-chart";
import { BarFacet } from "./bar-facet";
import { PieFacet } from "./pie-facet";
import { HistogramFacet } from "./histogram-facet";
import type { FacetBucket, FacetResult } from "../types";

/**
 * Layout config: maps backend facet field name to chart type.
 * Order here determines grid order.
 */
const FACET_LAYOUT: Array<{ field: string; chart: "bar" | "pie" }> = [
  { field: "base", chart: "bar" },
  { field: "is_deleted", chart: "pie" },
  { field: "is_hidden", chart: "pie" },
  { field: "is_processed", chart: "pie" },
  { field: "type_of_record", chart: "bar" },
  { field: "bibliographic_level", chart: "pie" },
  { field: "authority_link_linkers", chart: "bar" },
  { field: "authority_link_bases", chart: "bar" },
  { field: "comparators", chart: "bar" },
  { field: "comparison_bases", chart: "bar" },
  { field: "match_qualities", chart: "pie" },
  { field: "validators", chart: "bar" },
  { field: "validation_statuses", chart: "pie" },
  { field: "validation_target_tags", chart: "bar" },
  { field: "field_explanations", chart: "bar" },
];

/**
 * Maps backend facet field names to the URL param key in useRecordFilters.
 * Array facets map to their camelCase equivalents.
 * Boolean facets map to the boolean param name.
 */
const FACET_TO_URL_PARAM: Record<string, string> = {
  base: "bases",
  type_of_record: "typeOfRecord",
  bibliographic_level: "bibliographicLevel",
  is_deleted: "deleted",
  is_hidden: "hidden",
  is_processed: "processed",
  authority_link_linkers: "authorityLinkLinkers",
  authority_link_bases: "authorityLinkBases",
  comparators: "comparators",
  comparison_bases: "comparisonBases",
  match_qualities: "matchQualities",
  field_explanations: "fieldExplanations",
  validators: "validators",
  validation_statuses: "validationStatuses",
  validation_target_tags: "validationTargetTags",
};

/** Boolean facet labels → filter values */
const BOOL_LABEL_TO_VALUE: Record<string, Record<string, string>> = {
  deleted: { Deleted: "true", Active: "false" },
  hidden: { Hidden: "true", Visible: "false" },
  processed: { Processed: "true", Unprocessed: "false" },
};

export function PlotsView() {
  const { t } = useTranslation("records");
  const { filters, setFilters, toggleArrayFilter, setScoreRange } =
    useRecordFilters();
  const { data: facetsData, isLoading } = useFacets();
  const [hoveredField, setHoveredField] = useState<string | null>(null);
  const [hoveredValue, setHoveredValue] = useState<string | null>(null);

  const previewFacets = usePreviewForValue(
    hoveredField ?? "",
    hoveredValue,
  );

  if (isLoading) {
    return <p className="text-muted-foreground">{t("common:loading")}</p>;
  }

  if (!facetsData) {
    return <p className="text-muted-foreground">{t("plots.no-data")}</p>;
  }

  const facetsByField = new Map(facetsData.facets.map((f) => [f.field, f]));

  function getActiveValues(facetField: string): string[] {
    const paramKey = FACET_TO_URL_PARAM[facetField];
    if (!paramKey) return [];

    const paramValue = (filters as any)[paramKey];

    if (paramKey === "deleted" || paramKey === "hidden" || paramKey === "processed") {
      if (!paramValue) return [];
      const labelMap = BOOL_LABEL_TO_VALUE[paramKey];
      return Object.entries(labelMap)
        .filter(([, v]) => v === paramValue)
        .map(([label]) => label);
    }

    return Array.isArray(paramValue) ? paramValue : [];
  }

  function handleToggle(facetField: string, value: string) {
    const paramKey = FACET_TO_URL_PARAM[facetField];
    if (!paramKey) return;

    if (paramKey === "deleted" || paramKey === "hidden" || paramKey === "processed") {
      const labelMap = BOOL_LABEL_TO_VALUE[paramKey];
      const targetValue = labelMap[value];
      const currentValue = (filters as any)[paramKey];
      setFilters({
        [paramKey]: currentValue === targetValue ? "" : targetValue,
        page: 1,
      } as any);
    } else {
      toggleArrayFilter(paramKey as any, value);
    }
  }

  function getPreviewBuckets(facetField: string): FacetBucket[] | undefined {
    if (!previewFacets) return undefined;
    const result = previewFacets.facets.find(
      (f: FacetResult) => f.field === facetField,
    );
    return result?.buckets;
  }

  const scoreHistogram = facetsData.histograms.find(
    (h) => h.field === "overall_score",
  );

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t("plots.total-records", { count: facetsData.total })}
      </p>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
        {FACET_LAYOUT.map(({ field, chart }) => {
          const facetResult = facetsByField.get(field);
          if (!facetResult || facetResult.buckets.length === 0) return null;

          const activeValues = getActiveValues(field);
          const previewBuckets = getPreviewBuckets(field);

          return (
            <FacetChart
              key={field}
              title={t(`facet-fields.${field}`)}
              facetField={field}
              data={facetResult.buckets}
              previewData={previewBuckets}
              activeValues={activeValues}
              onToggle={(value) => handleToggle(field, value)}
              onHover={(value) => {
                setHoveredField(field);
                setHoveredValue(value);
              }}
              onLeave={() => {
                setHoveredField(null);
                setHoveredValue(null);
              }}
            >
              {(chartProps) =>
                chart === "bar" ? (
                  <BarFacet {...chartProps} />
                ) : (
                  <PieFacet {...chartProps} />
                )
              }
            </FacetChart>
          );
        })}

        {scoreHistogram && scoreHistogram.buckets.length > 0 && (
          <div className="col-span-full">
            <FacetChart
              title={t("facet-fields.overall_score")}
              facetField="overall_score"
              data={[]}
              activeValues={[]}
              onToggle={() => {}}
              onHover={() => {}}
              onLeave={() => {}}
            >
              {() => (
                <HistogramFacet
                  data={scoreHistogram.buckets}
                  onRangeChange={setScoreRange}
                />
              )}
            </FacetChart>
          </div>
        )}
      </div>
    </div>
  );
}
