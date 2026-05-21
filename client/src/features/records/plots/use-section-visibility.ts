import { parseAsString } from "nuqs";
import { useQueryStates } from "nuqs";
import { useCallback, useMemo } from "react";

/** All chart IDs that can be toggled, grouped by section. */
export const SECTION_GROUPS = {
  context: ["base", "comparators", "validators", "authority_link_linkers"],
  health: ["record_status", "match_quality", "validation_status"],
  classification: ["type_of_record", "bibliographic_level", "authority_link_bases"],
  analysis: ["overall_score", "field_explanations"],
} as const;

export type ChartId = (typeof SECTION_GROUPS)[keyof typeof SECTION_GROUPS][number];

const ALL_CHART_IDS: ChartId[] = Object.values(SECTION_GROUPS).flat() as ChartId[];

export function useSectionVisibility() {
  const [params, setParams] = useQueryStates(
    {
      hiddenCharts: parseAsString.withDefault(""),
    },
    { history: "replace" },
  );

  const hiddenSet = useMemo(() => {
    if (!params.hiddenCharts) return new Set<string>();
    return new Set(params.hiddenCharts.split(",").filter(Boolean));
  }, [params.hiddenCharts]);

  const isVisible = useCallback(
    (chartId: ChartId) => !hiddenSet.has(chartId),
    [hiddenSet],
  );

  const toggleChart = useCallback(
    (chartId: ChartId) => {
      const next = new Set(hiddenSet);
      if (next.has(chartId)) {
        next.delete(chartId);
      } else {
        next.add(chartId);
      }
      const value = [...next].join(",");
      setParams({ hiddenCharts: value || "" });
    },
    [hiddenSet, setParams],
  );

  const isSectionVisible = useCallback(
    (section: keyof typeof SECTION_GROUPS) => {
      return SECTION_GROUPS[section].some((id) => !hiddenSet.has(id));
    },
    [hiddenSet],
  );

  return { isVisible, toggleChart, isSectionVisible, hiddenSet, ALL_CHART_IDS };
}
