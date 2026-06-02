import { Fragment } from "react";
import { useTranslation } from "react-i18next";
import { FacetChart } from "./facet-chart";
import { BarFacet } from "./bar-facet";
import { RadialValidation, STATUS_COLORS } from "./radial-validation";
import type { FacetBucket } from "../types";
import type { ChartId } from "./use-section-visibility";
import { stripPrefix } from "../utils";

const REASON_TO_STATUS: Record<string, string> = {
  missing_link_text: "ForReview",
  invalid_link_format: "Invalid",
  no_links_found_or_expected: "Valid",
  non_top_level_document: "Invalid",
  non_linkable_model: "AdditionalInfo",
  valid_link: "Valid",
  link_not_found: "Invalid",
  missing_link_in_marc: "Invalid",
  wrong_path_found: "AdditionalInfo",
  wrong_path_not_found: "AdditionalInfo",
  wrong_server_found: "Invalid",
  wrong_server_not_found: "Invalid",
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
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {perValidatorData.map(({ validator, statuses, reasons }) =>
          statuses.length > 0 ? (
            <Fragment key={validator}>
              {isVisible("validation_status") && (
                <FacetChart
                  key={`status-${validator}`}
                  title={`${t(`validator-name.${validator}`, validator)}: ${t("facet-fields.validation_statuses")}`}
                  facetField="validation_statuses"
                  className="md:col-span-2 xl:col-span-1"
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
                  className="md:col-span-2 xl:col-span-2"
                >
                  {(chartProps) => {
                    const rawByTranslated = new Map(
                      chartProps.data.map((b) => {
                        const reason = stripPrefix(b.key);
                        return [t(`validation-reason.${reason}`, reason), b.key];
                      }),
                    );
                    const translatedData = chartProps.data.map((b) => ({
                      ...b,
                      key: t(`validation-reason.${stripPrefix(b.key)}`, stripPrefix(b.key)),
                    }));
                    const translatedPreview = chartProps.previewData?.map((b) => ({
                      ...b,
                      key: t(`validation-reason.${stripPrefix(b.key)}`, stripPrefix(b.key)),
                    }));
                    const labelIndicators: Record<string, string> = {};
                    for (const b of chartProps.data) {
                      const reason = stripPrefix(b.key);
                      const status = REASON_TO_STATUS[reason];
                      if (status && STATUS_COLORS[status]) {
                        const translatedKey = t(`validation-reason.${reason}`, reason);
                        labelIndicators[translatedKey] = STATUS_COLORS[status];
                      }
                    }
                    return (
                      <BarFacet
                        data={translatedData}
                        previewData={translatedPreview}
                        activeValues={chartProps.activeValues.map((v) =>
                          t(`validation-reason.${stripPrefix(v)}`, stripPrefix(v)),
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
            </Fragment>
          ) : null,
        )}
      </div>
    </section>
  );
}
