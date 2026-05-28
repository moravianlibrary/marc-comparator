import { useTranslation } from "react-i18next";
import { FacetChart } from "./facet-chart";
import { BarFacet } from "./bar-facet";
import { RadialValidation } from "./radial-validation";
import type { FacetBucket } from "../types";
import type { ChartId } from "./use-section-visibility";

interface ValidatorData {
  validator: string;
  statuses: FacetBucket[];
  reasons: FacetBucket[];
}

interface ValidationSectionProps {
  isVisible: (chart: ChartId) => boolean;
  getActiveValues: (field: string) => string[];
  getPreviewBuckets: (field: string) => FacetBucket[] | undefined;
  makeChartHandlers: (field: string) => {
    onToggle: (value: string) => void;
    onHover: (value: string) => void;
    onLeave: () => void;
  };
  perValidatorData: ValidatorData[];
}

export function ValidationSection({
  isVisible,
  getActiveValues,
  getPreviewBuckets,
  makeChartHandlers,
  perValidatorData,
}: ValidationSectionProps) {
  const { t } = useTranslation("records");

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        {t("plots.sections.validation")}
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {perValidatorData.map(({ validator, statuses, reasons }) =>
          statuses.length > 0 ? (
            <>
              {isVisible("validation_status") && (
                <FacetChart
                  key={`status-${validator}`}
                  title={`${t(`validator-name.${validator}`, validator)}: ${t("facet-fields.validation_statuses")}`}
                  facetField="validation_statuses"
                  data={statuses}
                  previewData={getPreviewBuckets("validation_statuses")}
                  activeValues={getActiveValues("validation_statuses")}
                  {...makeChartHandlers("validation_statuses")}
                  contentClassName="flex justify-center"
                >
                  {(chartProps) => <RadialValidation {...chartProps} />}
                </FacetChart>
              )}
              {isVisible("validation_reasons") && reasons.length > 0 && (
                <FacetChart
                  key={`reasons-${validator}`}
                  title={`${t(`validator-name.${validator}`, validator)}: ${t("facet-fields.validation_reasons")}`}
                  facetField="validation_reasons"
                  data={reasons}
                  previewData={getPreviewBuckets("validation_reasons")}
                  activeValues={getActiveValues("validation_reasons")}
                  {...makeChartHandlers("validation_reasons")}
                  className="md:col-span-2"
                >
                  {(chartProps) => {
                    const rawByTranslated = new Map(
                      chartProps.data.map((b) => [t(`validation-reason.${b.key}`, b.key), b.key]),
                    );
                    const translatedData = chartProps.data.map((b) => ({
                      ...b,
                      key: t(`validation-reason.${b.key}`, b.key),
                    }));
                    const translatedPreview = chartProps.previewData?.map((b) => ({
                      ...b,
                      key: t(`validation-reason.${b.key}`, b.key),
                    }));
                    return (
                      <BarFacet
                        data={translatedData}
                        previewData={translatedPreview}
                        activeValues={chartProps.activeValues.map(
                          (v) => t(`validation-reason.${v}`, v),
                        )}
                        onToggle={(translated) =>
                          chartProps.onToggle(rawByTranslated.get(translated) ?? translated)
                        }
                        onHover={(translated) =>
                          chartProps.onHover(rawByTranslated.get(translated) ?? translated)
                        }
                        onLeave={chartProps.onLeave}
                        labelWidth="50%"
                      />
                    );
                  }}
                </FacetChart>
              )}
            </>
          ) : null,
        )}
      </div>
    </section>
  );
}
