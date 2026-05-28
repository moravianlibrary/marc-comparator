import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useRecordFilters } from "../use-record-filters";
import {
  useFacets,
  usePrefetchFacetPreview,
  usePreviewForValue,
  usePerValidatorData,
} from "./use-facets";
import { SectionConfig } from "./section-config";
import { useSectionVisibility } from "./use-section-visibility";
import { ActiveFiltersBar, type ActiveFilter } from "./active-filters-bar";
import { ContextSection, type PillGroup } from "./context-section";
import { RecordsSection } from "./records-section";
import { ComparisonSection } from "./comparison-section";
import { ValidationSection } from "./validation-section";
import type { FacetBucket, FacetResult, HistogramBucket } from "../types";
import {
  SkeletonRecordsSection,
  SkeletonComparisonSection,
  SkeletonValidationSection,
} from "@/components/skeletons/skeleton-plots-section";

const FACET_TO_URL_PARAM: Record<string, string> = {
  base: "bases",
  type_of_record: "typeOfRecord",
  bibliographic_level: "bibliographicLevel",
  is_deleted: "deleted",
  is_processed: "processed",
  review_status: "reviewStatuses",
  authority_link_linkers: "authorityLinkLinkers",
  authority_link_bases: "authorityLinkBases",
  comparison_bases: "comparisonBases",
  match_qualities: "matchQualities",
  field_explanations: "fieldExplanations",
  validators: "validators",
  validation_statuses: "validationStatuses",
  validation_target_tags: "validationTargetTags",
  validation_reasons: "validationReasons",
};

const BOOL_LABEL_TO_VALUE: Record<string, Record<string, string>> = {
  deleted: { Deleted: "true", Active: "false" },
  processed: { Processed: "true", Unprocessed: "false" },
};

const EXPLANATION_ORDER: Record<string, number> = {
  Identical: 0,
  NonStandardized: 1,
  Typo: 2,
  Incomplete: 3,
  Incorrect: 4,
  Missing: 5,
};

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
  const prefetch = usePrefetchFacetPreview();
  const { isVisible, toggleChart, toggleSection, isSectionVisible } = useSectionVisibility();
  const perValidatorData = usePerValidatorData();

  const previewFacets = usePreviewForValue(
    hoveredField ?? "",
    hoveredValue,
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <SkeletonRecordsSection />
        <SkeletonComparisonSection />
        <SkeletonValidationSection />
      </div>
    );
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
    if (paramKey === "deleted" || paramKey === "processed") {
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
    if (paramKey === "deleted" || paramKey === "processed") {
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
    if (hasRecordIdFilter) return undefined;
    if (!previewFacets || facetField === hoveredField) return undefined;
    const result = previewFacets.facets.find(
      (f: FacetResult) => f.field === facetField,
    );
    return result?.buckets ?? [];
  }

  function getPreviewHistogramBuckets(field: string): HistogramBucket[] | undefined {
    if (hasRecordIdFilter) return undefined;
    if (!previewFacets || field === hoveredField) return undefined;
    const result = previewFacets.histograms.find((h) => h.field === field);
    return result?.buckets ?? [];
  }

  function makeChartHandlers(field: string) {
    return {
      onToggle: (value: string) => handleToggle(field, value),
      onHover: (value: string) => {
        if (hasRecordIdFilter) return;
        if (getActiveValues(field).includes(value)) return;
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
      return b.count - a.count;
    },
  );

  // Collect all active filters for the summary bar
  const allFacetFields = Object.keys(FACET_TO_URL_PARAM);
  const activeFilters: ActiveFilter[] = [];
  const VALUE_TRANSLATORS: Record<string, (v: string) => string> = {
    is_deleted: (v) => t(`state.${v}`),
    is_processed: (v) => t(`state.${v}`),
    review_status: (v) => t(`state.${v}`),
    type_of_record: (v) => t(`type-of-record.${v}`, { defaultValue: v }),
    bibliographic_level: (v) => t(`bibliographic-level.${v}`, { defaultValue: v }),
    validators: (v) => t(`validator-name.${v}`, { defaultValue: v }),
    match_qualities: (v) => t(`match-quality.${v}`, { defaultValue: v }),
    validation_statuses: (v) => t(`validity-status.${v}`, { defaultValue: v }),
    field_explanations: (v) => t(`field-explanation.${v}`, { defaultValue: v }),
    authority_link_linkers: (v) => t(`linker-name.${v}`, { defaultValue: v }),
    validation_reasons: (v) => t(`validation-reason.${v}`, { defaultValue: v }),
  };
  for (const field of allFacetFields) {
    const values = getActiveValues(field);
    const fieldLabel = t(`facet-fields.${field}`);
    const translator = VALUE_TRANSLATORS[field];
    for (const value of values) {
      activeFilters.push({
        facetField: field,
        label: fieldLabel,
        value,
        valueLabel: translator ? translator(value) : value,
      });
    }
  }
  const hasScoreFilter = filters.scoreMin > 0 || filters.scoreMax < 1;
  const hasRecordIdFilter = !!filters.recordId;
  const hasAnyFilter = activeFilters.length > 0 || hasScoreFilter || hasRecordIdFilter;

  // Context pill groups
  const contextFields: { field: string; label: string; formatLabel?: (k: string) => string }[] = [
    { field: "base", label: t("facet-fields.base") },
    {
      field: "authority_link_bases",
      label: t("facet-fields.authority_link_bases"),
    },
    {
      field: "authority_link_linkers",
      label: t("facet-fields.authority_link_linkers"),
      formatLabel: (k) => t(`linker-name.${k}`, { defaultValue: k }),
    },
    {
      field: "comparison_bases",
      label: t("facet-fields.comparison_bases"),
    },
    { field: "validators", label: t("facet-fields.validators"), formatLabel: (k) => t(`validator-name.${k}`, { defaultValue: k }) },
  ];

  const pillGroups: PillGroup[] = contextFields
    .filter(({ field }) => isVisible(field as any) && getBuckets(field).length > 0)
    .map(({ field, label, formatLabel }) => {
      const handlers = makeChartHandlers(field);
      return {
        label,
        facetField: field,
        buckets: getBuckets(field),
        previewBuckets: getPreviewBuckets(field),
        activeValues: getActiveValues(field),
        formatLabel,
        ...handlers,
        onHover: (value: string) => {
          if (!hasRecordIdFilter) prefetch(field);
          handlers.onHover(value);
        },
      };
    });

  const hasRecordsContent =
    (isVisible("record_status") && (getBuckets("is_deleted").length > 0 || getBuckets("review_status").length > 0 || getBuckets("is_processed").length > 0)) ||
    (isVisible("type_of_record") && getBuckets("type_of_record").length > 0) ||
    (isVisible("bibliographic_level") && getBuckets("bibliographic_level").length > 0);

  const hasComparisonContent =
    (isVisible("match_quality") && getBuckets("match_qualities").length > 0) ||
    (isVisible("overall_score") && scoreHistogram && scoreHistogram.buckets.length > 0) ||
    (isVisible("field_explanations") && explanationBuckets.length > 0);

  const hasValidationContent =
    perValidatorData && perValidatorData.some(({ statuses }) => statuses.length > 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {t("plots.total-records", { count: facetsData.total })}
        </p>
        <SectionConfig isVisible={isVisible} toggleChart={toggleChart} isSectionVisible={isSectionVisible} toggleSection={toggleSection} />
      </div>

      {hasAnyFilter && (
        <ActiveFiltersBar
          activeFilters={activeFilters}
          hasScoreFilter={hasScoreFilter}
          hasRecordIdFilter={hasRecordIdFilter}
          recordId={filters.recordId}
          scoreMin={filters.scoreMin}
          scoreMax={filters.scoreMax}
          onToggleFilter={handleToggle}
          onClearRecordId={() => setFilters({ recordId: "", recordIndex: 0 })}
          onClearScore={() => setScoreRange(0, 1)}
          onClearAll={clearFilters}
        />
      )}

      {isSectionVisible("context") && (pillGroups.length > 0 || hasRecordIdFilter) && (
        <ContextSection
          pillGroups={pillGroups}
          hasRecordIdFilter={hasRecordIdFilter}
          recordId={filters.recordId}
          onClearRecordId={() => setFilters({ recordId: "", recordIndex: 0 })}
        />
      )}

      {isSectionVisible("records") && hasRecordsContent && (
        <RecordsSection
          isVisible={isVisible}
          getBuckets={getBuckets}
          getActiveValues={getActiveValues}
          getPreviewBuckets={getPreviewBuckets}
          makeChartHandlers={makeChartHandlers}
          handleToggle={handleToggle}
          prefetch={prefetch}
          setHoveredField={setHoveredField}
          setHoveredValue={setHoveredValue}
        />
      )}

      {isSectionVisible("comparison") && hasComparisonContent && (
        <ComparisonSection
          isVisible={isVisible}
          getBuckets={getBuckets}
          getActiveValues={getActiveValues}
          getPreviewBuckets={getPreviewBuckets}
          getPreviewHistogramBuckets={getPreviewHistogramBuckets}
          makeChartHandlers={makeChartHandlers}
          scoreHistogramBuckets={scoreHistogram?.buckets ?? []}
          explanationBuckets={explanationBuckets}
          scoreMin={filters.scoreMin}
          scoreMax={filters.scoreMax}
          onScoreRangeChange={setScoreRange}
        />
      )}

      {isSectionVisible("validation") && hasValidationContent && (
        <ValidationSection
          isVisible={isVisible}
          getActiveValues={getActiveValues}
          getPreviewBuckets={getPreviewBuckets}
          makeChartHandlers={makeChartHandlers}
          perValidatorData={perValidatorData}
        />
      )}
    </div>
  );
}
