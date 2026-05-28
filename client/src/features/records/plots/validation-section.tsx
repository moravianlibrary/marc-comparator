import { useTranslation } from "react-i18next";
import { FacetChart } from "./facet-chart";
import { BarFacet } from "./bar-facet";
import { RadialValidation, STATUS_COLORS } from "./radial-validation";
import type { FacetBucket } from "../types";
import type { ChartId } from "./use-section-visibility";

const REASON_TO_STATUS: Record<string, string> = {
  "Missing link text in $y": "ForReview",
  "Invalid Kramerius link format": "Invalid",
  "Non-standard Kramerius link format": "AdditionalInfo",
  "Non-standard URL path": "AdditionalInfo",
  "Wrong Kramerius client URL": "AdditionalInfo",
  "No Kramerius links found or expected": "Valid",
  "Kramerius link points to non-top-level document": "Invalid",
  "Found Kramerius document with non-linkable model": "AdditionalInfo",
  "Valid Kramerius link": "Valid",
  "Link not found in Kramerius": "Invalid",
  "Missing Kramerius link in MARC": "Invalid",
};

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
                    const labelIndicators: Record<string, string> = {};
                    for (const b of chartProps.data) {
                      const status = REASON_TO_STATUS[b.key];
                      if (status && STATUS_COLORS[status]) {
                        const translatedKey = t(`validation-reason.${b.key}`, b.key);
                        labelIndicators[translatedKey] = STATUS_COLORS[status];
                      }
                    }
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
                        labelIndicators={labelIndicators}
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
