import type {
    EsHistogramAggregation,
    EsHistogramBucket,
    EsTermsBucket,
} from "../../models/api/responses/es_aggregations";
import type { CollectionData } from "../collection/domain";
import type { EsState } from "./domain";

export const selectSelectedCount = <T>(
    state: EsState,
    data: CollectionData<T>
): number =>
    state.isAllSelected ? data.totalItems ?? 0 : state.selectedIds.size;

function getNestedAgg<T>(
    data: CollectionData<T> | undefined,
    field: string,
    isNested: boolean
): any | undefined {
    if (!data?.aggregations) return undefined;

    if (!isNested) {
        return data.aggregations[field];
    }

    const parts = field.split(".");
    let node: any = data.aggregations;

    for (let i = 0; i < parts.length; i++) {
        const key = parts[i];
        node = node?.[key];

        if (!node) return undefined;
    }

    return node;
}

export function selectTermsBuckets<T>(
    field: string,
    state: EsState,
    data?: CollectionData<T>,
    bucketsOrdering?: (a: EsTermsBucket, b: EsTermsBucket) => number
): EsTermsBucket[] {
    const isNested = state.config.filters?.[field]?.nested === true;

    const agg = getNestedAgg(data, field, isNested) as
        | undefined
        | { buckets: EsTermsBucket[] };

    if (!agg?.buckets) return [];

    const buckets = [...agg.buckets];
    if (bucketsOrdering) {
        return buckets.sort(bucketsOrdering);
    }

    return buckets.sort((a, b) => {
        if (b.doc_count !== a.doc_count) {
            return b.doc_count - a.doc_count;
        }
        if (a.key < b.key) return -1;
        if (a.key > b.key) return 1;
        return 0;
    });
}

export function selectHistogramBuckets<T>(
    field: string,
    state: EsState,
    data?: CollectionData<T>
): EsHistogramBucket[] {
    const isNested = state.config.filters?.[field]?.nested === true;

    const agg = getNestedAgg(data, field, isNested) as
        | undefined
        | EsHistogramAggregation;

    return agg?.buckets ?? [];
}
