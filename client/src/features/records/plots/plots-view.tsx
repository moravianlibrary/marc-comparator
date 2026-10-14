import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  SkeletonComparisonSection,
  SkeletonRecordsSection,
  SkeletonValidationSection,
} from '@/components/skeletons/skeleton-plots-section';
import type { FacetBucket, FacetResult, HistogramBucket } from '../types';
import { MATCH_SCALE_MAX } from '../score';
import type { ArrayFilterKey, BoolFilterKey } from '../use-record-filters';
import { isBoolFilterKey, useRecordFilters } from '../use-record-filters';
import { type ActiveFilter, ActiveFiltersBar } from './active-filters-bar';
import { ComparisonSection } from './comparison-section';
import type { PillGroup } from './facet-pills';
import { LinkingSection } from './linking-section';
import { RecordsSection } from './records-section';
import { SectionConfig } from './section-config';
import {
  useFacets,
  usePerValidatorData,
  usePrefetchFacetPreview,
  usePreviewForValue,
} from './use-facets';
import type { ChartId, SectionKey } from './use-section-visibility';
import { useSectionVisibility } from './use-section-visibility';
import { ValidationSection } from './validation-section';

type FilterKey = ArrayFilterKey | BoolFilterKey;

const FACET_TO_URL_PARAM: Partial<Record<string, FilterKey>> = {
  base: 'bases',
  type_of_record: 'typeOfRecord',
  bibliographic_level: 'bibliographicLevel',
  is_deleted: 'deleted',
  is_processed: 'processed',
  has_alternatives: 'hasAlternatives',
  has_claim: 'hasClaim',
  claim_needs_review: 'claimNeedsReview',
  review_status: 'reviewStatuses',
  authority_link_linkers: 'authorityLinkLinkers',
  authority_link_bases: 'authorityLinkBases',
  link_outcomes: 'linkOutcomes',
  link_agencies: 'linkAgencies',
  link_identifiers: 'linkIdentifiers',
  comparison_bases: 'comparisonBases',
  match_qualities: 'matchQualities',
  field_explanations: 'fieldExplanations',
  validators: 'validators',
  validation_statuses: 'validationStatuses',
  validation_target_tags: 'validationTargetTags',
  validation_reasons: 'validationReasons',
};

// The bucket labels a boolean facet comes back with, mapped to the tri-state
// the URL carries. Membership here is also what marks a param as boolean, so
// adding a boolean facet is one entry rather than one entry and two `||`s.
//
// `has_alternatives` and `claim_needs_review` also come back with a third
// bucket for the records the question does not arise for. It is deliberately
// absent here: the filter behind it is a boolean and has no way to say "is
// undefined", so the bucket is shown and counted but clicking it only clears
// the filter rather than inventing a state the API cannot express.
const BOOL_LABEL_TO_VALUE: Record<string, Record<string, string>> = {
  deleted: { Deleted: 'true', Active: 'false' },
  processed: { Processed: 'true', Unprocessed: 'false' },
  hasAlternatives: { 'Has alternatives': 'true', 'Single candidate': 'false' },
  hasClaim: { "Cataloguer's answer": 'true', 'No cataloguer ruling': 'false' },
  claimNeedsReview: { 'Claim needs review': 'true', 'Claim holds': 'false' },
};

// How many pills a context group shows before it collapses behind a count.
//
// Eleven of the twelve groups have four values or fewer and never reach it.
// The twelfth is the cataloguing agency of the linked record: 263 values,
// 187 of them naming ten records or fewer and 84 naming exactly one. Printed
// in full it was longer than the rest of the dashboard put together, and it
// also set the cost of hovering one of its pills, because a preview is a
// pass over the analytics table per value.
const PILL_LIMIT = 12;

const EXPLANATION_ORDER: Record<string, number> = {
  Identical: 0,
  NonStandardized: 1,
  Typo: 2,
  Incomplete: 3,
  Incorrect: 4,
  Missing: 5,
};

export function PlotsView() {
  const { t } = useTranslation('records');
  const { filters, setFilters, toggleArrayFilter, setBoolFilter, setScoreRange, clearFilters } =
    useRecordFilters();
  const { data: facetsData, isLoading } = useFacets();
  const [hoveredField, setHoveredField] = useState<string | null>(null);
  const [hoveredValue, setHoveredValue] = useState<string | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<ReadonlySet<string>>(() => new Set());
  const [groupSearch, setGroupSearch] = useState<Record<string, string>>({});
  const prefetch = usePrefetchFacetPreview();
  const { isVisible, toggleChart, toggleSection, isSectionVisible } = useSectionVisibility();
  const perValidatorData = usePerValidatorData();

  // Defined up here, above the loading guard, because the preview a hover
  // reads has to be looked up under the same scope it was fetched with, and
  // that lookup is a hook.
  const facetsByField = new Map((facetsData?.facets ?? []).map(f => [f.field, f]));

  function getBuckets(field: string): FacetBucket[] {
    return facetsByField.get(field)?.buckets ?? [];
  }

  function isCollapsible(field: string): boolean {
    return getBuckets(field).length > PILL_LIMIT;
  }

  /**
   * Whether a preview will be computed live rather than read from the cube.
   *
   * The server uses the precomputed cube only when nothing is filtered. With
   * any filter it falls back to scanning the analytics table once per value
   * asked about — 2.4s a value against 344k records, and they contend, so
   * twelve values measured 34s rather than the twelve-eighths of that the
   * thread pool suggests.
   *
   * `hasAnyFilter` further down says the same thing, but is declared after
   * the hook that needs this.
   */
  const previewIsLive =
    Object.keys(FACET_TO_URL_PARAM).some(f => getActiveValues(f).length > 0) ||
    filters.scoreMin > 0 ||
    filters.scoreMax < MATCH_SCALE_MAX ||
    !!filters.recordId;

  /**
   * The pills a context group is actually showing: searched, then capped.
   *
   * A value being filtered on is always among them, whatever the search says
   * and wherever it falls in the order. Hiding it would leave a filter in
   * force with nothing on screen to switch it back off.
   */
  function visibleBuckets(field: string): FacetBucket[] {
    const all = getBuckets(field);
    if (all.length <= PILL_LIMIT) {
      return all;
    }
    const active = new Set(getActiveValues(field));
    const needle = (groupSearch[field] ?? '').trim().toLowerCase();
    const matching = needle
      ? all.filter(b => active.has(b.key) || b.key.toLowerCase().includes(needle))
      : all;
    if (expandedGroups.has(field)) {
      return matching;
    }
    const capped = matching.slice(0, PILL_LIMIT);
    const shown = new Set(capped.map(b => b.key));
    return [...capped, ...matching.filter(b => active.has(b.key) && !shown.has(b.key))];
  }

  /**
   * The values to ask a preview for, or undefined to ask for all of them.
   *
   * A preview costs the server a pass over the analytics table per value, so
   * what this returns is a bound on the work one hover can start.
   *
   * When the answer comes from the cube it is one indexed read whatever is
   * asked for, so a collapsed group asks about the dozen pills it is showing
   * and running along the row costs one request instead of twelve. A group
   * short enough not to collapse asks for nothing in particular, which
   * leaves its request and its cache entry exactly as they were.
   *
   * When the answer has to be computed live every extra value is another
   * pass over the analytics table, and prefetching a row nobody has pointed
   * at yet is most of the bill: asking for all 263 agencies measured 677s,
   * the visible twelve 34s, and the one pill under the cursor 2.4s. So a
   * live preview asks about that pill and nothing else.
   */
  function previewScope(field: string, value: string | null): string[] | undefined {
    if (previewIsLive) {
      return value ? [value] : undefined;
    }
    if (!isCollapsible(field)) {
      return undefined;
    }
    if (!expandedGroups.has(field)) {
      return visibleBuckets(field).map(b => b.key);
    }
    return value ? [value] : undefined;
  }

  const previewFacets = usePreviewForValue(
    hoveredField ?? '',
    hoveredValue,
    hoveredField ? previewScope(hoveredField, hoveredValue) : undefined,
  );

  if (isLoading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <SkeletonRecordsSection />
        <SkeletonComparisonSection />
        <SkeletonValidationSection />
      </div>
    );
  }

  if (!facetsData) {
    return <p className="text-muted-foreground">{t('plots.no-data')}</p>;
  }

  function getActiveValues(facetField: string): string[] {
    const paramKey = FACET_TO_URL_PARAM[facetField];
    if (!paramKey) {
      return [];
    }
    const paramValue = filters[paramKey];
    if (isBoolFilterKey(paramKey)) {
      if (!paramValue) {
        return [];
      }
      const labelMap = BOOL_LABEL_TO_VALUE[paramKey]!;
      return Object.entries(labelMap)
        .filter(([, v]) => v === paramValue)
        .map(([label]) => label);
    }
    return Array.isArray(paramValue) ? paramValue : [];
  }

  function handleToggle(facetField: string, value: string) {
    const paramKey = FACET_TO_URL_PARAM[facetField];
    if (!paramKey) {
      return;
    }
    if (isBoolFilterKey(paramKey)) {
      const targetValue = BOOL_LABEL_TO_VALUE[paramKey]![value] ?? '';
      const currentValue = filters[paramKey];
      setBoolFilter(paramKey, currentValue === targetValue ? '' : targetValue);
      return;
    }

    toggleArrayFilter(paramKey, value);
  }

  function getPreviewBuckets(facetField: string): FacetBucket[] | undefined {
    if (hasRecordIdFilter) {
      return undefined;
    }
    if (!previewFacets || facetField === hoveredField) {
      return undefined;
    }
    const result = previewFacets.facets.find((f: FacetResult) => f.field === facetField);
    return result?.buckets ?? [];
  }

  function getPreviewHistogramBuckets(field: string): HistogramBucket[] | undefined {
    if (hasRecordIdFilter) {
      return undefined;
    }
    if (!previewFacets || field === hoveredField) {
      return undefined;
    }
    const result = previewFacets.histograms.find(h => h.field === field);
    return result?.buckets ?? [];
  }

  function makeChartHandlers(field: string) {
    return {
      onToggle: (value: string) => handleToggle(field, value),
      onHover: (value: string) => {
        if (hasRecordIdFilter) {
          return;
        }
        if (getActiveValues(field).includes(value)) {
          return;
        }
        setHoveredField(field);
        setHoveredValue(value);
      },
      onLeave: () => {
        setHoveredField(null);
        setHoveredValue(null);
      },
    };
  }

  const scoreHistogram = facetsData.histograms.find(h => h.field === 'overall_score');

  const explanationBuckets = [...getBuckets('field_explanations')].sort((a, b) => {
    const orderA = EXPLANATION_ORDER[a.key] ?? Number.MAX_SAFE_INTEGER;
    const orderB = EXPLANATION_ORDER[b.key] ?? Number.MAX_SAFE_INTEGER;
    if (orderA !== orderB) {
      return orderA - orderB;
    }
    return b.count - a.count;
  });

  // Collect all active filters for the summary bar
  const allFacetFields = Object.keys(FACET_TO_URL_PARAM);
  const activeFilters: ActiveFilter[] = [];
  const VALUE_TRANSLATORS: Record<string, (v: string) => string> = {
    is_deleted: v => t(`state.${v}`),
    is_processed: v => t(`state.${v}`),
    has_alternatives: v => t(`alternatives.${v}`, { defaultValue: v }),
    has_claim: v => t(`claim-presence.${v}`, { defaultValue: v }),
    claim_needs_review: v => t(`claim-review.${v}`, { defaultValue: v }),
    review_status: v => t(`state.${v}`),
    type_of_record: v => t(`type-of-record.${v}`, { defaultValue: v }),
    bibliographic_level: v => t(`bibliographic-level.${v}`, { defaultValue: v }),
    validators: v => t(`validator-name.${v}`, { defaultValue: v }),
    match_qualities: v => t(`match-quality.${v}`, { defaultValue: v }),
    validation_statuses: v => {
      const s = v.includes(':') ? v.slice(v.indexOf(':') + 1) : v;
      return t(`validity-status.${s}`, { defaultValue: s });
    },
    field_explanations: v => t(`field-explanation.${v}`, { defaultValue: v }),
    authority_link_linkers: v => t(`linker-name.${v}`, { defaultValue: v }),
    validation_reasons: v => {
      const r = v.includes(':') ? v.slice(v.indexOf(':') + 1) : v;
      return t(`validation-reason.${r}`, { defaultValue: r });
    },
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
  const hasScoreFilter = filters.scoreMin > 0 || filters.scoreMax < MATCH_SCALE_MAX;
  const hasRecordIdFilter = !!filters.recordId;
  const hasAnyFilter = activeFilters.length > 0 || hasScoreFilter || hasRecordIdFilter;

  // The facets shown as pills rather than as a chart, each filed under the
  // section that owns the question it answers. Order within a section is the
  // order they appear in; it follows SECTION_GROUPS.
  const pillFields: {
    field: ChartId;
    section: SectionKey;
    label: string;
    formatLabel?: (k: string) => string;
  }[] = [
    { field: 'base', section: 'records', label: t('facet-fields.base') },
    {
      field: 'link_outcomes',
      section: 'linking',
      label: t('facet-fields.link_outcomes'),
      formatLabel: k => t(`link-outcome-short.${k}`, { defaultValue: k }),
    },
    {
      field: 'authority_link_linkers',
      section: 'linking',
      label: t('facet-fields.authority_link_linkers'),
      formatLabel: k => t(`linker-name.${k}`, { defaultValue: k }),
    },
    {
      field: 'has_alternatives',
      section: 'linking',
      label: t('facet-fields.has_alternatives'),
      formatLabel: k => t(`alternatives.${k}`, { defaultValue: k }),
    },
    {
      field: 'link_agencies',
      section: 'linking',
      label: t('facet-fields.link_agencies'),
    },
    {
      field: 'link_identifiers',
      section: 'linking',
      label: t('facet-fields.link_identifiers'),
      formatLabel: k => t(`match-identifier.${k}`, { defaultValue: k }),
    },
    {
      field: 'authority_link_bases',
      section: 'linking',
      label: t('facet-fields.authority_link_bases'),
    },
    {
      field: 'has_claim',
      section: 'linking',
      label: t('facet-fields.has_claim'),
      formatLabel: k => t(`claim-presence.${k}`, { defaultValue: k }),
    },
    {
      field: 'claim_needs_review',
      section: 'linking',
      label: t('facet-fields.claim_needs_review'),
      formatLabel: k => t(`claim-review.${k}`, { defaultValue: k }),
    },
    {
      field: 'comparison_bases',
      section: 'comparison',
      label: t('facet-fields.comparison_bases'),
    },
    {
      field: 'validators',
      section: 'validation',
      label: t('facet-fields.validators'),
      formatLabel: k => t(`validator-name.${k}`, { defaultValue: k }),
    },
  ];

  /**
   * A facet whose one bucket holds the whole catalogue, which is not a filter.
   *
   * `has_claim` and `claim_needs_review` are both in this state until a
   * cataloguer decides something: one pill reading "Bez rozhodnutí 344 660",
   * which selects every record and so narrows nothing. Hidden rather than
   * removed — the first ruling makes them real again on their own.
   */
  function isDegenerate(field: string): boolean {
    // Never a facet being filtered on. Filtering base to MZK01 leaves the
    // base facet with one bucket holding every remaining record, which looks
    // exactly like a facet that never discriminated — and hiding it would
    // take away the pill that switches the filter back off.
    if (getActiveValues(field).length > 0) {
      return false;
    }
    const [only, ...rest] = getBuckets(field);
    return only !== undefined && rest.length === 0 && only.count === facetsData?.total;
  }

  const pillGroupEntries: [SectionKey, PillGroup][] = pillFields
    .filter(({ field }) => isVisible(field) && getBuckets(field).length > 0 && !isDegenerate(field))
    .map(({ field, section, label, formatLabel }) => {
      const handlers = makeChartHandlers(field);
      const group: PillGroup = {
        label,
        facetField: field,
        buckets: visibleBuckets(field),
        totalBuckets: getBuckets(field).length,
        collapsible: isCollapsible(field),
        expanded: expandedGroups.has(field),
        onToggleExpanded: () =>
          setExpandedGroups(current => {
            const next = new Set(current);
            if (!next.delete(field)) {
              next.add(field);
            }
            return next;
          }),
        search: groupSearch[field] ?? '',
        onSearchChange: (value: string) =>
          setGroupSearch(current => ({ ...current, [field]: value })),
        previewBuckets: getPreviewBuckets(field),
        activeValues: getActiveValues(field),
        formatLabel,
        ...handlers,
        onHover: (value: string) => {
          if (!hasRecordIdFilter) {
            prefetch(field, previewScope(field, value));
          }
          handlers.onHover(value);
        },
      };
      return [section, group];
    });

  function pillGroupsFor(section: SectionKey): PillGroup[] {
    return pillGroupEntries.filter(([s]) => s === section).map(([, group]) => group);
  }

  // A section renders when it has either a chart or a pill row to show. The
  // pill rows count: `linking` has no charts of its own yet, and without
  // them in the test it would never appear.
  const hasRecordsContent =
    pillGroupsFor('records').length > 0 ||
    (isVisible('record_status') &&
      (getBuckets('is_deleted').length > 0 ||
        getBuckets('review_status').length > 0 ||
        getBuckets('is_processed').length > 0)) ||
    (isVisible('type_of_record') && getBuckets('type_of_record').length > 0) ||
    (isVisible('bibliographic_level') && getBuckets('bibliographic_level').length > 0);

  const hasLinkingContent = pillGroupsFor('linking').length > 0;

  const hasComparisonContent =
    pillGroupsFor('comparison').length > 0 ||
    (isVisible('match_quality') && getBuckets('match_qualities').length > 0) ||
    (isVisible('overall_score') && scoreHistogram && scoreHistogram.buckets.length > 0) ||
    (isVisible('field_explanations') && explanationBuckets.length > 0);

  const hasValidationContent =
    pillGroupsFor('validation').length > 0 ||
    perValidatorData?.some(({ statuses }) => statuses.length > 0);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {t('plots.total-records', { count: facetsData.total })}
        </p>
        <SectionConfig
          isVisible={isVisible}
          toggleChart={toggleChart}
          isSectionVisible={isSectionVisible}
          toggleSection={toggleSection}
        />
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
          onClearRecordId={() => setFilters({ recordId: '', recordIndex: 0 })}
          onClearScore={() => setScoreRange(0, 1)}
          onClearAll={clearFilters}
        />
      )}

      {isSectionVisible('records') && hasRecordsContent && (
        <RecordsSection
          pillGroups={pillGroupsFor('records')}
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

      {isSectionVisible('linking') && hasLinkingContent && (
        <LinkingSection pillGroups={pillGroupsFor('linking')} />
      )}

      {isSectionVisible('comparison') && hasComparisonContent && (
        <ComparisonSection
          pillGroups={pillGroupsFor('comparison')}
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

      {isSectionVisible('validation') && hasValidationContent && (
        <ValidationSection
          pillGroups={pillGroupsFor('validation')}
          isVisible={isVisible}
          getActiveValues={getActiveValues}
          getPreviewBuckets={getPreviewBuckets}
          makeChartHandlers={makeChartHandlers}
          // May be empty now: the section also renders for its pill row,
          // which is there before any validator has reported anything.
          perValidatorData={perValidatorData ?? []}
        />
      )}
    </div>
  );
}
