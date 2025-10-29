import type { EsRequest } from "../models/api/requests/es";

export function buildTermsAggregation(field: string, models: any[]) {
    const counts: Record<string, number> = {};

    models.forEach((m) => {
        const key = m.attrs[field] ?? "undefined";

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

export function buildSearchResponse(
    schema: any,
    request: any,
    collection: string,
    idFunc?: (model: any) => string
) {
    const esRequest = JSON.parse(request.requestBody) as EsRequest;
    const { query, from, size, aggs } = esRequest;

    const hits = schema
        .all(collection)
        .models.filter((p: any) => query.match_all)
        .slice(from || 0, (from || 0) + (size || 10))
        .map((p: any) => {
            const { id, ...rest } = p.attrs;
            return {
                _index: collection,
                _id: idFunc ? idFunc(p) : String(p.id),
                _source: rest,
            };
        });

    const totalItems = schema.all(collection).length;

    const aggregationResults: Record<string, any> = {};
    if (aggs) {
        for (const [aggName, aggDef] of Object.entries(aggs)) {
            if ("terms" in (aggDef as any)) {
                const field = (aggDef as any).terms.field;
                aggregationResults[aggName] = buildTermsAggregation(
                    field,
                    schema.all(collection).models
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
