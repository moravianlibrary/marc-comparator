import { type Dispatch, Fragment, type ReactElement } from "react";
import type {
    CollectionAction,
    CollectionState,
} from "../../store/collection/domain";
import {
    Button,
    Card,
    CardBody,
    CardTitle,
    Divider,
    Label,
    LabelGroup,
} from "@patternfly/react-core";
import {
    EsTermsAggregationSchema,
    EsHistogramAggregationSchema,
} from "../../models/api/responses/es_aggregations";
import type {
    EsAggregation,
    EsHistogramAggregation,
    EsTermsAggregation,
    EsTermsBucket,
} from "../../models/api/responses/es_aggregations";
import type {
    FilterConfig,
    TermsFilterConfig,
    TermsFilterState,
    HistogramFilterConfig,
    HistogramFilterState,
} from "../../models/ui/filters";
import { ResourcesEmptyIcon, ResourcesFullIcon } from "@patternfly/react-icons";
import RangeSlider from "./RangeSlider";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { useTranslation } from "react-i18next";

interface RecordsTableFiltersProps {
    state: CollectionState<CatalogRecord>;
    dispatch: Dispatch<CollectionAction>;
    aggregations: Record<string, EsAggregation>;
}

const TermsFilter = ({
    config,
    state,
    aggregation,
    toggleBucket,
}: {
    config: TermsFilterConfig;
    state?: TermsFilterState;
    aggregation: EsTermsAggregation;
    toggleBucket: (field: string, bucketKey: string) => void;
}): ReactElement => {
    const { t } = useTranslation();
    const bucketsOrdering = (a: EsTermsBucket, b: EsTermsBucket) => {
        if (config.displayOrder) {
            return (
                config.displayOrder.indexOf(a.key.toString()) -
                config.displayOrder.indexOf(b.key.toString())
            );
        }
        return (
            b.doc_count - a.doc_count ||
            a.key.toString().localeCompare(b.key.toString())
        );
    };

    const bucketLabel = (bucket: EsTermsBucket) => {
        const bucketKey = bucket.key_as_string || bucket.key.toString();
        if (config.labelI18nKey) {
            return t(config.labelI18nKey(bucketKey));
        }
        return bucketKey;
    };

    return (
        <Card isPlain key={config.field}>
            <CardTitle>
                {t(`records:fields.${config.field.replaceAll("_", "-")}`)}
            </CardTitle>
            <CardBody>
                <LabelGroup numLabels={state?.size || config.sizeOptions[0]}>
                    {aggregation.buckets.sort(bucketsOrdering).map((bucket) => (
                        <Button
                            size="sm"
                            key={bucket.key.toString()}
                            variant={
                                state?.include.includes(bucket.key.toString())
                                    ? "secondary"
                                    : "tertiary"
                            }
                            icon={
                                state &&
                                state.include.includes(
                                    bucket.key.toString()
                                ) ? (
                                    <ResourcesFullIcon />
                                ) : (
                                    <ResourcesEmptyIcon color="grey" />
                                )
                            }
                            countOptions={{
                                count: bucket.doc_count,
                                isRead: !state?.include.includes(
                                    bucket.key.toString()
                                ),
                            }}
                            onClick={() =>
                                toggleBucket(
                                    config.field,
                                    bucket.key.toString()
                                )
                            }
                        >
                            {config.labelProps ? (
                                <Label
                                    {...config.labelProps(
                                        bucket.key.toString()
                                    )}
                                >
                                    {bucketLabel(bucket)}
                                </Label>
                            ) : (
                                bucketLabel(bucket)
                            )}
                        </Button>
                    ))}
                </LabelGroup>
            </CardBody>
        </Card>
    );
};

const HistogramFilter = ({
    config,
    state,
    aggregation,
    setRange,
}: {
    config: HistogramFilterConfig;
    state?: HistogramFilterState;
    aggregation: EsHistogramAggregation;
    setRange: (field: string, from?: number, to?: number) => void;
}): ReactElement => {
    const { t } = useTranslation();
    const allKeys = aggregation.buckets.map((b) => b.key);
    if (allKeys.length === 0) {
        return <div>No histogram data available</div>;
    }

    const min = config.min ?? Math.min(...allKeys);
    const max = config.max ?? Math.max(...allKeys);

    const from = state?.from ?? min;
    const to = state?.to ?? max;

    // Convert histogram buckets to midpoint data for RangeSlider
    const histogramData = aggregation.buckets.map((b, i, arr) => {
        const nextKey = arr[i + 1]?.key ?? b.key + config.interval;
        const x = (b.key + nextKey) / 2;
        const y = b.doc_count;
        return { x, y };
    });

    return (
        <Card isPlain key={config.field}>
            <CardTitle>
                {t(`records:fields.${config.field.replaceAll("_", "-")}`)}
            </CardTitle>
            <CardBody>
                <RangeSlider
                    min={min}
                    max={max}
                    from={from}
                    to={to}
                    histogramData={histogramData}
                    onChange={(from, to) => setRange(config.field, from, to)}
                />
            </CardBody>
        </Card>
    );
};

function isEsAggregation(obj: any): obj is EsAggregation {
    if (!obj || typeof obj !== "object") return false;

    return Array.isArray(obj.buckets);
}

function getAggregation(
    aggregations: Record<string, any>,
    field: string
): EsAggregation | undefined {
    const parts = field.split(".");

    let current: any = aggregations;

    for (let i = 0; i < parts.length; i++) {
        const key = parts[i];

        if (!current || typeof current !== "object") return undefined;

        // Step into the next level
        current = current[key];
        if (!current) return undefined;

        // If this is NOT the last part, drill into nested sub-aggregations
        if (i < parts.length - 1) {
            if (current.aggs) {
                current = current.aggs;
            } else if (current.aggregations) {
                current = current.aggregations;
            } else {
                // It's a container aggregation (doc_count but no explicit aggs)
                // so stay in this object (it contains nested keys directly)
                // e.g. field_results → subfield_results
                continue;
            }
        }
    }

    // At the end of traversal, we must return an actual aggregation
    if (isEsAggregation(current)) return current;

    return undefined;
}

const RecordsTableFilters = ({
    state,
    dispatch,
    aggregations,
}: RecordsTableFiltersProps): ReactElement => {
    const {
        config: { filter: config },
        filterStates,
    } = state;

    const renderFilter = (filterConfig: FilterConfig) => {
        const aggregation = getAggregation(aggregations, filterConfig.field);

        if (!aggregation) {
            return null;
        }
        if (aggregation.buckets.length === 0) {
            return null;
        }

        if (filterConfig.type === "term") {
            const parsed = EsTermsAggregationSchema.safeParse(aggregation);
            if (!parsed.success) {
                return null;
            }

            return (
                <TermsFilter
                    key={filterConfig.field}
                    config={filterConfig}
                    state={
                        filterStates?.[filterConfig.field] as
                            | TermsFilterState
                            | undefined
                    }
                    aggregation={parsed.data}
                    toggleBucket={(field: string, bucketKey: string) => {
                        dispatch({ type: "toggleTerm", field, bucketKey });
                    }}
                />
            );
        }

        if (filterConfig.type === "histogram") {
            const parsed = EsHistogramAggregationSchema.safeParse(aggregation);
            if (!parsed.success) {
                return null;
            }

            return (
                <HistogramFilter
                    key={filterConfig.field}
                    config={filterConfig}
                    state={
                        filterStates?.[filterConfig.field] as
                            | HistogramFilterState
                            | undefined
                    }
                    aggregation={parsed.data}
                    setRange={(field: string, from?: number, to?: number) => {
                        dispatch({
                            type: "setHistogramRange",
                            field,
                            from,
                            to,
                        });
                    }}
                />
            );
        }
    };
    const renderedFilters = config
        .map((filterConfig) => renderFilter(filterConfig))
        .filter(Boolean);

    return (
        <Fragment>
            {renderedFilters.flatMap((el, index) =>
                index === renderedFilters.length - 1
                    ? [el]
                    : [el, <Divider key={index} />]
            )}
        </Fragment>
    );
};

export default RecordsTableFilters;
