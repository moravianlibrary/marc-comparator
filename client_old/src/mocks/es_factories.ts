import type { EsRequest } from "../models/api/requests/es";

function getValuesByPath(obj: any, path: string[]): any[] {
    if (!obj) return [];

    const [key, ...rest] = path;

    if (Array.isArray(obj)) {
        return obj.flatMap((item) => getValuesByPath(item, path));
    }

    const value = obj[key];

    if (rest.length === 0) {
        if (Array.isArray(value)) {
            return Array.from(new Set(value));
        } else if (value !== undefined && value !== null) {
            return [value];
        } else {
            return [];
        }
    }

    return getValuesByPath(value, rest);
}

export function buildTermsAggregation(field: string, models: any[]) {
    const counts: Record<string, number> = {};

    models.forEach((m) => {
        const key = getValuesByPath(m.attrs, field.split(".")) ?? "undefined";

        if (Array.isArray(key)) {
            key.forEach((k) => {
                counts[k] = (counts[k] || 0) + 1;
            });
            return;
        }

        counts[key] = (counts[key] || 0) + 1;
    });

    return {
        buckets: Object.entries(counts).map(([key, doc_count]) => ({
            key,
            doc_count,
        })),
        sum_other_doc_count: 0,
        doc_count_error_upper_bound: 0,
    };
}

export function buildRangeAggregation(
    field: string,
    models: any[],
    ranges: Array<{ from?: number; to?: number }>
) {
    const path = field.split(".");
    const buckets = ranges.map((range) => {
        let doc_count = 0;

        models.forEach((m) => {
            const values = getValuesByPath(m.attrs, path);
            if (
                values
                    .filter((v) => typeof v === "number")
                    .some(
                        (v) =>
                            (range.from === undefined || v >= range.from) &&
                            (range.to === undefined || v < range.to)
                    )
            ) {
                doc_count += 1;
            }
        });

        return {
            key: `${range.from ?? "*"}-${range.to ?? "*"}`,
            from: range.from,
            to: range.to,
            doc_count,
        };
    });

    return { buckets };
}

export function buildHistogramAggregation(
    field: string,
    models: any[],
    interval: number
) {
    const path = field.split(".");
    const values: number[] = [];

    // Flatten all numeric values at the path
    models.forEach((m) => {
        const v = getValuesByPath(m.attrs, path).filter(
            (x) => typeof x === "number"
        ) as number[];
        values.push(...v);
    });

    if (values.length === 0) {
        return { buckets: [] };
    }

    const min = Math.min(...values);
    const max = Math.max(...values);

    // Compute number of buckets
    const bucketCount = Math.ceil((max - min) / interval);

    const buckets: { key: number; doc_count: number }[] = Array.from(
        { length: bucketCount },
        (_, i) => ({
            key: min + i * interval,
            doc_count: 0,
        })
    );

    // Count values into buckets
    values.forEach((v) => {
        const index = Math.floor((v - min) / interval);
        const bucketIndex = Math.min(index, buckets.length - 1);
        buckets[bucketIndex].doc_count += 1;
    });

    return { buckets };
}

function matchQuery(
    model: any,
    query: any,
    idFunc?: (model: any) => string
): boolean {
    if (query.match_all) return true;

    if (query.term) {
        return Object.entries(query.term).every(([field, value]) => {
            const fieldValue =
                field === "_id"
                    ? idFunc
                        ? idFunc(model)
                        : model.attrs["id"]
                    : model.attrs[field] ?? model[field];
            return fieldValue === value;
        });
    }

    if (query.bool) {
        let must = query.bool.must ?? [];
        let filter = query.bool.filter ?? [];

        // Ensure arrays
        must = Array.isArray(must) ? must : [must];
        filter = Array.isArray(filter) ? filter : [filter];

        const mustPass = must.every((q: any) => matchQuery(model, q));
        const filterPass = filter.every((q: any) => matchQuery(model, q));

        return mustPass && filterPass;
    }

    if (query.range) {
        return Object.entries(query.range).every(([field, condRaw]) => {
            const cond = condRaw as {
                gte?: number | string;
                lte?: number | string;
                gt?: number | string;
                lt?: number | string;
            };
            const val = model.attrs[field] ?? model[field];
            if (cond.gte !== undefined && val < cond.gte) return false;
            if (cond.lte !== undefined && val > cond.lte) return false;
            return true;
        });
    }

    return false;
}

export function buildSearchResponse(
    schema: any,
    request: any,
    collection: string,
    idFunc?: (model: any) => string
) {
    const esRequest = JSON.parse(request.requestBody) as EsRequest;
    const { query, from, size, aggs } = esRequest;

    const models = schema
        .all(collection)
        .models.filter((m: any) => matchQuery(m, query, idFunc));

    const hits = models
        .slice(from || 0, (from || 0) + (size || 10))
        .map((p: any) => {
            const { id, ...rest } = p.attrs;
            return {
                _index: collection,
                _id: idFunc ? idFunc(p) : String(p.id),
                _source: rest,
            };
        });

    const totalItems = models.length;

    const aggregationResults: Record<string, any> = {};
    if (aggs) {
        for (const [aggName, aggDef] of Object.entries(aggs)) {
            if ("terms" in (aggDef as any)) {
                const field = (aggDef as any).terms.field;
                aggregationResults[aggName] = buildTermsAggregation(
                    field,
                    models
                );
            } else if ("range" in (aggDef as any)) {
                const field = (aggDef as any).range.field;
                const ranges = (aggDef as any).range.ranges;
                aggregationResults[aggName] = buildRangeAggregation(
                    field,
                    models,
                    ranges
                );
            } else if ("histogram" in (aggDef as any)) {
                const field = (aggDef as any).histogram.field;
                const interval = (aggDef as any).histogram.interval;
                aggregationResults[aggName] = buildHistogramAggregation(
                    field,
                    models,
                    interval
                );
            }
            // Optionally: handle range, date_range, etc.
        }
    }

    return {
        took: 1,
        timed_out: false,
        _shards: { total: 1, successful: 1, failed: 0 },
        hits: { total: { value: totalItems }, hits },
        aggregations: aggregationResults,
    };
}
