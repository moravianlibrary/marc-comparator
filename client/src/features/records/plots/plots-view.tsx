import { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRecordFilters } from "../use-record-filters";
import {
  useFacets,
  usePrefetchFacetPreview,
  usePreviewForValue,
  usePerValidatorStatuses,
} from "./use-facets";
import { FacetChart } from "./facet-chart";
import { BarFacet } from "./bar-facet";
import { DonutFacet } from "./donut-facet";
import { StatusTripleFacet } from "./status-triple-facet";
import { HistogramFacet } from "./histogram-facet";
import { ContextPills } from "./context-pills";
import { RadialQuality } from "./radial-quality";
import { RadialValidation } from "./radial-validation";
import { SectionConfig } from "./section-config";
import { useSectionVisibility } from "./use-section-visibility";
import type { FacetBucket, FacetResult, HistogramBucket } from "../types";

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

const BOOL_LABEL_TO_VALUE: Record<string, Record<string, string>> = {
  deleted: { Deleted: "true", Active: "false" },
  hidden: { Hidden: "true", Visible: "false" },
  processed: { Processed: "true", Unprocessed: "false" },
};

const EXPLANATION_ORDER: Record<string, number> = {
  IDENTICAL: 0,
  NON_STANDARDIZED: 1,
  TYPO: 2,
  INCOMPLETE: 3,
  INCORRECT: 4,
  MISSING: 5,
};

function ScoreRangeInputs({
  scoreMin,
  scoreMax,
  onChange,
}: {
  scoreMin: number;
  scoreMax: number;
  onChange: (from: number, to: number) => void;
}) {
  const minRef = useRef<HTMLInputElement>(null);
  const maxRef = useRef<HTMLInputElement>(null);

  function handleSubmit() {
    const rawMin = Number(minRef.current?.value);
    const rawMax = Number(maxRef.current?.value);
    if (Number.isNaN(rawMin) || Number.isNaN(rawMax)) return;
    const clampedMin = Math.max(0, Math.min(rawMin, 100));
    const clampedMax = Math.max(clampedMin, Math.min(rawMax, 100));
    if (minRef.current) minRef.current.value = String(clampedMin);
    if (maxRef.current) maxRef.current.value = String(clampedMax);
    onChange(clampedMin / 100, clampedMax / 100);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
      (e.target as HTMLInputElement).blur();
    }
  }

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <input
        ref={minRef}
        type="number"
        min={0}
        max={100}
        key={scoreMin}
        defaultValue={Math.round(scoreMin * 100)}
        onKeyDown={handleKeyDown}
        onBlur={handleSubmit}
        className="h-6 w-14 rounded border border-input bg-background px-1.5 text-xs tabular-nums text-center"
      />
      <span className="text-muted-foreground">–</span>
      <input
        ref={maxRef}
        type="number"
        min={0}
        max={100}
        key={scoreMax}
        defaultValue={Math.round(scoreMax * 100)}
        onKeyDown={handleKeyDown}
        onBlur={handleSubmit}
        className="h-6 w-14 rounded border border-input bg-background px-1.5 text-xs tabular-nums text-center"
      />
      <span className="text-muted-foreground">%</span>
    </div>
  );
}

export function PlotsView() {
  const { t } = useTranslation("records");
  const {
    filters,
    setFilters,
    toggleArrayFilter,
    setScoreRange,
    clearFilters,
  } = useRecordFilters();
  const { data: facetsData, isLoading } = useFacets();
  const [hoveredField, setHoveredField] = useState<string | null>(null);
  const [hoveredValue, setHoveredValue] = useState<string | null>(null);
  const [showAllExplanations, setShowAllExplanations] = useState(false);
  const prefetch = usePrefetchFacetPreview();
  const { isVisible, toggleChart, toggleSection, isSectionVisible } = useSectionVisibility();
  const perValidatorStatuses = usePerValidatorStatuses();

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

  function getBuckets(field: string): FacetBucket[] {
    return facetsByField.get(field)?.buckets ?? [];
  }

  function getActiveValues(facetField: string): string[] {
    const paramKey = FACET_TO_URL_PARAM[facetField];
    if (!paramKey) return [];
    const paramValue = (filters as any)[paramKey];
    if (
      paramKey === "deleted" ||
      paramKey === "hidden" ||
      paramKey === "processed"
    ) {
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
    if (
      paramKey === "deleted" ||
      paramKey === "hidden" ||
      paramKey === "processed"
    ) {
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
    if (!previewFacets || facetField === hoveredField) return undefined;
    const result = previewFacets.facets.find(
      (f: FacetResult) => f.field === facetField,
    );
    return result?.buckets ?? [];
  }

  function getPreviewHistogramBuckets(field: string): HistogramBucket[] | undefined {
    if (!previewFacets || field === hoveredField) return undefined;
    const result = previewFacets.histograms.find((h) => h.field === field);
    return result?.buckets ?? [];
  }

  function makeChartHandlers(field: string) {
    return {
      onToggle: (value: string) => handleToggle(field, value),
      onHover: (value: string) => {
        setHoveredField(field);
        setHoveredValue(value);
      },
      onLeave: () => {
        setHoveredField(null);
        setHoveredValue(null);
      },
    };
  }

  const scoreHistogram = facetsData.histograms.find(
    (h) => h.field === "overall_score",
  );

  const explanationBuckets = [...getBuckets("field_explanations")].sort(
    (a, b) => {
      const orderA = EXPLANATION_ORDER[a.key] ?? Number.MAX_SAFE_INTEGER;
      const orderB = EXPLANATION_ORDER[b.key] ?? Number.MAX_SAFE_INTEGER;
      if (orderA !== orderB) return orderA - orderB;
      return b.count - a.count; // fallback: by count descending
    },
  );
  const visibleExplanations = showAllExplanations
    ? explanationBuckets
    : explanationBuckets.slice(0, 10);

  // Collect all active filters for the summary bar
  const allFacetFields = Object.keys(FACET_TO_URL_PARAM);
  const activeFilters: {
    facetField: string;
    label: string;
    value: string;
    valueLabel: string;
  }[] = [];
  for (const field of allFacetFields) {
    const values = getActiveValues(field);
    const fieldLabel = t(`facet-fields.${field}`);
    for (const value of values) {
      const boolFields = ["is_deleted", "is_hidden", "is_processed"];
      const valueLabel = boolFields.includes(field)
        ? t(`state.${value}`)
        : value;
      activeFilters.push({
        facetField: field,
        label: fieldLabel,
        value,
        valueLabel,
      });
    }
  }
  const hasScoreFilter = filters.scoreMin > 0 || filters.scoreMax < 1;
  const hasAnyFilter = activeFilters.length > 0 || hasScoreFilter;

  // Context pill groups
  const contextFields = [
    { field: "base", label: t("facet-fields.base") },
    { field: "comparators", label: t("facet-fields.comparators") },
    { field: "validators", label: t("facet-fields.validators") },
    {
      field: "authority_link_linkers",
      label: t("facet-fields.authority_link_linkers"),
    },
  ];

  const pillGroups = contextFields
    .filter(({ field }) => isVisible(field as any) && getBuckets(field).length > 0)
    .map(({ field, label }) => ({
      label,
      facetField: field,
      buckets: getBuckets(field),
      previewBuckets: getPreviewBuckets(field),
      activeValues: getActiveValues(field),
      ...makeChartHandlers(field),
    }));

  return (
    <div className="space-y-6">
      {/* Header: total count + filters + section config */}
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {t("plots.total-records", { count: facetsData.total })}
        </p>
        <SectionConfig isVisible={isVisible} toggleChart={toggleChart} isSectionVisible={isSectionVisible} toggleSection={toggleSection} />
      </div>

      {hasAnyFilter && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">
            {t("plots.active-filters")}:
          </span>
          {activeFilters.map((af) => (
            <Badge
              key={`${af.facetField}-${af.value}`}
              variant="secondary"
              className="gap-1 cursor-pointer"
              onClick={() => handleToggle(af.facetField, af.value)}
            >
              <span className="text-muted-foreground">{af.label}:</span>{" "}
              {af.valueLabel}
              <X className="h-3 w-3" />
            </Badge>
          ))}
          {hasScoreFilter && (
            <Badge
              variant="secondary"
              className="gap-1 cursor-pointer"
              onClick={() => setScoreRange(0, 1)}
            >
              <span className="text-muted-foreground">
                {t("facet-fields.overall_score")}:
              </span>{" "}
              {(filters.scoreMin * 100).toFixed(0)}–
              {(filters.scoreMax * 100).toFixed(0)}%
              <X className="h-3 w-3" />
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-xs text-muted-foreground"
            onClick={clearFilters}
          >
            {t("plots.clear-all")}
          </Button>
        </div>
      )}

      {/* Row 1: Kontext (Context Controls) */}
      {isSectionVisible("context") && pillGroups.length > 0 && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            {t("plots.sections.context")}
          </h3>
          <Card>
            <CardContent className="flex flex-wrap gap-x-6 gap-y-3 pt-4">
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
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        </section>
      )}

      {/* Row 2: Stav kvality (Operational Health) */}
      {isSectionVisible("health") && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            {t("plots.sections.health")}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Card 1: Record Status */}
            {isVisible("record_status") && (
              <Card
                className={cn(
                  (getActiveValues("is_deleted").length > 0 ||
                    getActiveValues("is_hidden").length > 0 ||
                    getActiveValues("is_processed").length > 0) &&
                    "ring-2 ring-primary/30",
                )}
                onMouseEnter={() => {
                  prefetch("is_deleted");
                  prefetch("is_hidden");
                  prefetch("is_processed");
                }}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">
                    {t("plots.record-status")}
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
                        positiveKey: "Active",
                        negativeKey: "Deleted",
                      },
                      {
                        label: t("facet-fields.is_hidden"),
                        facetField: "is_hidden",
                        buckets: getBuckets("is_hidden"),
                        previewBuckets: getPreviewBuckets("is_hidden"),
                        positiveKey: "Visible",
                        negativeKey: "Hidden",
                      },
                      {
                        label: t("facet-fields.is_processed"),
                        facetField: "is_processed",
                        buckets: getBuckets("is_processed"),
                        previewBuckets: getPreviewBuckets("is_processed"),
                        positiveKey: "Processed",
                        negativeKey: "Unprocessed",
                      },
                    ]}
                    activeValues={{
                      is_deleted: getActiveValues("is_deleted"),
                      is_hidden: getActiveValues("is_hidden"),
                      is_processed: getActiveValues("is_processed"),
                    }}
                    onToggle={handleToggle}
                    onHover={(field, value) => {
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

            {/* Card 2: Match Quality */}
            {isVisible("match_quality") &&
              getBuckets("match_qualities").length > 0 && (
                <FacetChart
                  title={t("facet-fields.match_qualities")}
                  facetField="match_qualities"
                  data={getBuckets("match_qualities")}
                  previewData={getPreviewBuckets("match_qualities")}
                  activeValues={getActiveValues("match_qualities")}
                  {...makeChartHandlers("match_qualities")}
                >
                  {(chartProps) => <RadialQuality {...chartProps} />}
                </FacetChart>
              )}

            {/* Card 3+: Validation Status (one per validator) */}
            {isVisible("validation_status") &&
              perValidatorStatuses &&
              perValidatorStatuses.map(({ validator, statuses }) =>
                statuses.length > 0 ? (
                  <FacetChart
                    key={validator}
                    title={`${t("facet-fields.validation_statuses")} — ${validator}`}
                    facetField="validation_statuses"
                    data={statuses}
                    previewData={getPreviewBuckets("validation_statuses")}
                    activeValues={getActiveValues("validation_statuses")}
                    {...makeChartHandlers("validation_statuses")}
                  >
                    {(chartProps) => <RadialValidation {...chartProps} />}
                  </FacetChart>
                ) : null,
              )}
          </div>
        </section>
      )}

      {/* Row 3: Klasifikace zaznamov (Record Composition) */}
      {isSectionVisible("classification") && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            {t("plots.sections.classification")}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {isVisible("type_of_record") &&
              getBuckets("type_of_record").length > 0 && (
                <FacetChart
                  title={t("facet-fields.type_of_record")}
                  facetField="type_of_record"
                  data={getBuckets("type_of_record")}
                  previewData={getPreviewBuckets("type_of_record")}
                  activeValues={getActiveValues("type_of_record")}
                  {...makeChartHandlers("type_of_record")}
                >
                  {(chartProps) => <BarFacet {...chartProps} />}
                </FacetChart>
              )}

            {isVisible("bibliographic_level") &&
              getBuckets("bibliographic_level").length > 0 && (
                <FacetChart
                  title={t("facet-fields.bibliographic_level")}
                  facetField="bibliographic_level"
                  data={getBuckets("bibliographic_level")}
                  previewData={getPreviewBuckets("bibliographic_level")}
                  activeValues={getActiveValues("bibliographic_level")}
                  {...makeChartHandlers("bibliographic_level")}
                >
                  {(chartProps) => <DonutFacet {...chartProps} />}
                </FacetChart>
              )}

            {isVisible("authority_link_bases") &&
              getBuckets("authority_link_bases").length > 0 && (
                <FacetChart
                  title={t("facet-fields.authority_link_bases")}
                  facetField="authority_link_bases"
                  data={getBuckets("authority_link_bases")}
                  previewData={getPreviewBuckets("authority_link_bases")}
                  activeValues={getActiveValues("authority_link_bases")}
                  {...makeChartHandlers("authority_link_bases")}
                >
                  {(chartProps) => <BarFacet {...chartProps} />}
                </FacetChart>
              )}
          </div>
        </section>
      )}

      {/* Row 4: Analyza porovnani (Deep Analysis) */}
      {isSectionVisible("analysis") && (
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            {t("plots.sections.analysis")}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {isVisible("overall_score") &&
              scoreHistogram &&
              scoreHistogram.buckets.length > 0 && (
                <FacetChart
                  title={t("facet-fields.overall_score")}
                  facetField="overall_score"
                  data={[]}
                  activeValues={[]}
                  onToggle={() => {}}
                  onHover={() => {}}
                  onLeave={() => {}}
                  headerRight={
                    <ScoreRangeInputs
                      scoreMin={filters.scoreMin}
                      scoreMax={filters.scoreMax}
                      onChange={setScoreRange}
                    />
                  }
                >
                  {() => (
                    <HistogramFacet
                      data={scoreHistogram.buckets}
                      previewData={getPreviewHistogramBuckets("overall_score")}
                    />
                  )}
                </FacetChart>
              )}

            {isVisible("field_explanations") &&
              explanationBuckets.length > 0 && (
                <FacetChart
                  title={t("facet-fields.field_explanations")}
                  facetField="field_explanations"
                  data={visibleExplanations}
                  previewData={getPreviewBuckets("field_explanations")}
                  activeValues={getActiveValues("field_explanations")}
                  {...makeChartHandlers("field_explanations")}
                >
                  {(chartProps) => {
                    const rawByTranslated = new Map(
                      chartProps.data.map((b) => [t(`field-explanation.${b.key}`, b.key), b.key]),
                    );
                    const translatedData = chartProps.data.map((b) => ({
                      ...b,
                      key: t(`field-explanation.${b.key}`, b.key),
                    }));
                    const translatedPreview = chartProps.previewData?.map((b) => ({
                      ...b,
                      key: t(`field-explanation.${b.key}`, b.key),
                    }));
                    return (
                      <div>
                        <BarFacet
                          data={translatedData}
                          previewData={translatedPreview}
                          activeValues={chartProps.activeValues.map(
                            (v) => t(`field-explanation.${v}`, v),
                          )}
                          onToggle={(translated) =>
                            chartProps.onToggle(rawByTranslated.get(translated) ?? translated)
                          }
                          onHover={(translated) =>
                            chartProps.onHover(rawByTranslated.get(translated) ?? translated)
                          }
                          onLeave={chartProps.onLeave}
                        />
                        {explanationBuckets.length > 10 && (
                          <button
                            className="text-xs text-muted-foreground hover:text-foreground mt-2"
                            onClick={() =>
                              setShowAllExplanations(!showAllExplanations)
                            }
                          >
                            {showAllExplanations
                              ? t("plots.show-less")
                              : t("plots.show-all")}
                          </button>
                        )}
                      </div>
                    );
                  }}
                </FacetChart>
              )}
          </div>
        </section>
      )}
    </div>
  );
}
