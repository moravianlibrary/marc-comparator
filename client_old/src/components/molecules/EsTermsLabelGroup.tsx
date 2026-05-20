import type { Dispatch, ReactElement } from "react";
import type {
    EsState,
    EsStateAction,
    EsTermsFilterConfig,
} from "../../store/es/domain";
import type { CollectionData } from "../../store/collection/domain";
import type { EsTermsBucket } from "../../models/api/responses/es_aggregations";
import {
    Button,
    Card,
    CardBody,
    CardTitle,
    Divider,
    Label,
    LabelGroup,
    type LabelProps,
} from "@patternfly/react-core";
import { selectTermsBuckets } from "../../store/es/selectors";
import { ResourcesEmptyIcon, ResourcesFullIcon } from "@patternfly/react-icons";

const EsTermsLabelGroup = <T,>({
    field,
    data,
    state,
    dispatch,
    bucketsOrder,
    bucketsOrdering,
    renderBucketLabel,
    title,
    labelProps,
}: {
    field: string;
    data?: CollectionData<T>;
    state: EsState;
    dispatch: Dispatch<EsStateAction>;
    bucketsOrder?: string[];
    bucketsOrdering?: (a: EsTermsBucket, b: EsTermsBucket) => number;
    renderBucketLabel?: (bucket: EsTermsBucket) => React.ReactNode | null;
    title?: React.ReactNode;
    labelProps?: (bucketKey: string) => LabelProps | null;
}): ReactElement | null => {
    const config = state.config.filters?.[field] as
        | EsTermsFilterConfig
        | undefined;
    if (!config) return null;

    const filterState = state.terms?.[field];
    const include = new Set(filterState?.include || []);

    const bucketsOrderingFromOrder = bucketsOrder?.reduce((acc, key) => {
        acc[key] = true;
        return acc;
    }, {} as Record<string, boolean>);
    const bucketsOrderingFinal = bucketsOrderingFromOrder
        ? (a: EsTermsBucket, b: EsTermsBucket) => {
              const aIdx = bucketsOrder?.indexOf(a.key.toString()) || -1;
              const bIdx = bucketsOrder?.indexOf(b.key.toString()) || -1;
              return aIdx - bIdx;
          }
        : bucketsOrdering;

    const buckets = selectTermsBuckets(
        field,
        state,
        data,
        bucketsOrderingFinal
    );
    if (buckets.length === 0) return null;

    const renderLabel = (bucket: EsTermsBucket) => {
        const currLabelProps = labelProps && labelProps(bucket.key.toString());
        if (currLabelProps) {
            return <Label {...currLabelProps}>{bucket.key.toString()}</Label>;
        }

        return renderBucketLabel ? (
            renderBucketLabel(bucket)
        ) : (
            <>{bucket.key.toString()}</>
        );
    };

    return (
        <Card isPlain isCompact key={field}>
            <CardTitle>{title || field}</CardTitle>
            <Divider />
            <CardBody>
                <LabelGroup numLabels={filterState?.size || config.size}>
                    {buckets.map((bucket) => (
                        <Button
                            size="sm"
                            key={bucket.key.toString()}
                            variant={
                                include.has(bucket.key.toString())
                                    ? "secondary"
                                    : "tertiary"
                            }
                            icon={
                                include.has(bucket.key.toString()) ? (
                                    <ResourcesFullIcon />
                                ) : (
                                    <ResourcesEmptyIcon color="grey" />
                                )
                            }
                            countOptions={{
                                count: bucket.doc_count,
                                isRead: !include.has(bucket.key.toString()),
                            }}
                            onClick={() =>
                                dispatch({
                                    type: "toggleTerm",
                                    field,
                                    bucketKey: bucket.key.toString(),
                                })
                            }
                        >
                            {renderLabel(bucket)}
                        </Button>
                    ))}
                </LabelGroup>
            </CardBody>
        </Card>
    );
};

export default EsTermsLabelGroup;
