import { useState } from "react";
import { useTranslation } from "react-i18next";
import { FacetChart } from "./facet-chart";
import { BarFacet } from "./bar-facet";
import { HistogramFacet } from "./histogram-facet";
import { RadialQuality } from "./radial-quality";
import { ScoreRangeInputs } from "./score-range-inputs";
import type { FacetBucket, HistogramBucket } from "../types";
import type { ChartId } from "./use-section-visibility";

interface ComparisonSectionProps {
  isVisible: (chart: ChartId) => boolean;
  getBuckets: (field: string) => FacetBucket[];
  getActiveValues: (field: string) => string[];
  getPreviewBuckets: (field: string) => FacetBucket[] | undefined;
  getPreviewHistogramBuckets: (field: string) => HistogramBucket[] | undefined;
  makeChartHandlers: (field: string) => {
    onToggle: (value: string) => void;
    onHover: (value: string) => void;
    onLeave: () => void;
  };
  scoreHistogramBuckets: HistogramBucket[];
  explanationBuckets: FacetBucket[];
  scoreMin: number;
  scoreMax: number;
  onScoreRangeChange: (from: number, to: number) => void;
}

export function ComparisonSection({
  isVisible,
  getBuckets,
  getActiveValues,
  getPreviewBuckets,
  getPreviewHistogramBuckets,
  makeChartHandlers,
  scoreHistogramBuckets,
  explanationBuckets,
  scoreMin,
  scoreMax,
  onScoreRangeChange,
}: ComparisonSectionProps) {
  const { t } = useTranslation("records");
  const [showAllExplanations, setShowAllExplanations] = useState(false);

  const visibleExplanations = showAllExplanations
    ? explanationBuckets
    : explanationBuckets.slice(0, 10);

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        {t("plots.sections.comparison")}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {isVisible("match_quality") && getBuckets("match_qualities").length > 0 && (
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

        {isVisible("overall_score") && scoreHistogramBuckets.length > 0 && (
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
                scoreMin={scoreMin}
                scoreMax={scoreMax}
                onChange={onScoreRangeChange}
              />
            }
          >
            {() => (
              <HistogramFacet
                data={scoreHistogramBuckets}
                previewData={getPreviewHistogramBuckets("overall_score")}
              />
            )}
          </FacetChart>
        )}

        {isVisible("field_explanations") && explanationBuckets.length > 0 && (
          <FacetChart
            title={t("facet-fields.field_explanations")}
            facetField="field_explanations"
            className="md:col-span-2 xl:col-span-1"
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
                    activeValues={chartProps.activeValues.map((v) =>
                      t(`field-explanation.${v}`, v),
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
                      onClick={() => setShowAllExplanations(!showAllExplanations)}
                    >
                      {showAllExplanations ? t("plots.show-less") : t("plots.show-all")}
                    </button>
                  )}
                </div>
              );
            }}
          </FacetChart>
        )}
      </div>
    </section>
  );
}
