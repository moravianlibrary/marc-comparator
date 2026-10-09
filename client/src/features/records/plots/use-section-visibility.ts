import { parseAsString, useQueryStates } from 'nuqs';
import { useCallback, useEffect, useMemo } from 'react';

const STORAGE_KEY = 'plots:hiddenCharts';

/**
 * All chart IDs that can be toggled, grouped by section.
 *
 * There used to be a fifth section called "context" holding eleven facets.
 * It was not a subject the way the other three are — it was where anything
 * went that had no section, and eight of its eleven were about linking,
 * which is the one thing this tool does and the one section the dashboard
 * did not have. Its contents are now in the section that owns them and
 * `linking` exists, so a facet has exactly one place it can be.
 *
 * Order inside a section is display order. Each list leads with its pill
 * rows and then its charts.
 */
export const SECTION_GROUPS = {
  records: ['base', 'record_status', 'type_of_record', 'bibliographic_level'],
  linking: [
    'link_outcomes',
    'authority_link_linkers',
    'has_alternatives',
    'link_agencies',
    'link_identifiers',
    'authority_link_bases',
    'has_claim',
    'claim_needs_review',
  ],
  comparison: ['comparison_bases', 'match_quality', 'overall_score', 'field_explanations'],
  validation: ['validators', 'validation_status', 'validation_reasons'],
} as const;

export type SectionKey = keyof typeof SECTION_GROUPS;

export type ChartId = (typeof SECTION_GROUPS)[keyof typeof SECTION_GROUPS][number];

const ALL_CHART_IDS: ChartId[] = Object.values(SECTION_GROUPS).flat() as ChartId[];

export function useSectionVisibility() {
  const [params, setParams] = useQueryStates(
    {
      hiddenCharts: parseAsString.withDefault(localStorage.getItem(STORAGE_KEY) ?? ''),
    },
    { history: 'replace', shallow: true },
  );

  const hiddenSet = useMemo(() => {
    if (!params.hiddenCharts) {
      return new Set<string>();
    }
    return new Set(params.hiddenCharts.split(',').filter(Boolean));
  }, [params.hiddenCharts]);

  // Persist to localStorage whenever hiddenCharts changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, params.hiddenCharts);
  }, [params.hiddenCharts]);

  const isVisible = useCallback((chartId: ChartId) => !hiddenSet.has(chartId), [hiddenSet]);

  const toggleChart = useCallback(
    (chartId: ChartId) => {
      const next = new Set(hiddenSet);
      if (next.has(chartId)) {
        next.delete(chartId);
      } else {
        next.add(chartId);
      }
      const value = [...next].join(',');
      setParams({ hiddenCharts: value || '' });
    },
    [hiddenSet, setParams],
  );

  const isSectionVisible = useCallback(
    (section: keyof typeof SECTION_GROUPS) => {
      return SECTION_GROUPS[section].some(id => !hiddenSet.has(id));
    },
    [hiddenSet],
  );

  const toggleSection = useCallback(
    (section: keyof typeof SECTION_GROUPS) => {
      const ids = SECTION_GROUPS[section];
      const anyVisible = ids.some(id => !hiddenSet.has(id));
      const next = new Set(hiddenSet);
      for (const id of ids) {
        if (anyVisible) {
          next.add(id);
        } else {
          next.delete(id);
        }
      }
      const value = [...next].join(',');
      setParams({ hiddenCharts: value || '' });
    },
    [hiddenSet, setParams],
  );

  return { isVisible, toggleChart, toggleSection, isSectionVisible, hiddenSet, ALL_CHART_IDS };
}
