import { Fragment } from 'react';
import { useTranslation } from 'react-i18next';
import type { FacetBucket } from '../types';
import { stripPrefix } from '../utils';
import { BarFacet } from './bar-facet';
import { FacetChart } from './facet-chart';
import { FacetPillRows, type PillGroup } from './facet-pills';
import { RadialValidation, STATUS_COLORS } from './radial-validation';
import type { ChartId } from './use-section-visibility';

/**
 * The dot colour beside each reason in the chart.
 *
 * The facet buckets are keyed by validator and reason only, so the status has
 * to be restated here. That makes this a copy of what the validator decides:
 * a reason missing from the map silently renders without a dot rather than
 * failing, so it has to be extended whenever the validator gains a reason.
 */
const REASON_TO_STATUS: Record<string, string> = {
  no_links_found_or_expected: 'Valid',
  valid_link: 'Valid',
  missing_link_in_marc: 'Invalid',
  non_top_level_document: 'Invalid',
  link_not_found: 'Invalid',
  non_canonical_url_not_found: 'Invalid',
  non_canonical_url_found: 'ForReview',
  missing_link_text: 'ForReview',
  identifier_matches_multiple_documents: 'ForReview',
  non_linkable_model: 'ForReview',
  invalid_link_format: 'ForReview',
  foreign_digital_library: 'AdditionalInfo',
};

interface ValidatorData {
  validator: string;
  statuses: FacetBucket[];
  reasons: FacetBucket[];
}

interface ValidationSectionProps {
  pillGroups: PillGroup[];
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
  pillGroups,
  isVisible,
  getActiveValues,
  getPreviewBuckets,
  makeChartHandlers,
  perValidatorData,
}: ValidationSectionProps) {
  const { t } = useTranslation('records');

  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
        {t('plots.sections.validation')}
      </h3>
      <FacetPillRows groups={pillGroups} />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {perValidatorData.map(({ validator, statuses, reasons }) =>
          statuses.length > 0 ? (
            <Fragment key={validator}>
              {isVisible('validation_status') && (
                <FacetChart
                  key={`status-${validator}`}
                  title={`${t(`validator-name.${validator}`, validator)}: ${t('facet-fields.validation_statuses')}`}
                  facetField="validation_statuses"
                  className="md:col-span-2 xl:col-span-1"
                  data={statuses}
                  previewData={getPreviewBuckets('validation_statuses')}
                  activeValues={getActiveValues('validation_statuses')}
                  {...makeChartHandlers('validation_statuses')}
                  contentClassName="flex justify-center"
                >
                  {chartProps => <RadialValidation {...chartProps} />}
                </FacetChart>
              )}
              {isVisible('validation_reasons') && reasons.length > 0 && (
                <FacetChart
                  key={`reasons-${validator}`}
                  title={`${t(`validator-name.${validator}`, validator)}: ${t('facet-fields.validation_reasons')}`}
                  facetField="validation_reasons"
                  data={reasons}
                  previewData={getPreviewBuckets('validation_reasons')}
                  activeValues={getActiveValues('validation_reasons')}
                  {...makeChartHandlers('validation_reasons')}
                  className="md:col-span-2 xl:col-span-2"
                >
                  {chartProps => {
                    const rawByTranslated = new Map(
                      chartProps.data.map(b => {
                        const reason = stripPrefix(b.key);
                        return [t(`validation-reason.${reason}`, reason), b.key];
                      }),
                    );
                    const translatedData = chartProps.data.map(b => ({
                      ...b,
                      key: t(`validation-reason.${stripPrefix(b.key)}`, stripPrefix(b.key)),
                    }));
                    const translatedPreview = chartProps.previewData?.map(b => ({
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
                        activeValues={chartProps.activeValues.map(v =>
                          t(`validation-reason.${stripPrefix(v)}`, stripPrefix(v)),
                        )}
                        onToggle={translated =>
                          chartProps.onToggle(rawByTranslated.get(translated) ?? translated)
                        }
                        onHover={translated =>
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
