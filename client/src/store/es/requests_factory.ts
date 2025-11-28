import type { EsRequest } from "../../models/api/requests/es";
import type {
    EsFilterConfig,
    EsFilterState,
    EsState,
    EsTermsFilterState,
} from "./domain";

function weightedFields(
    fields: string[],
    weights: Record<string, number> | undefined
): string[] {
    return weights
        ? fields.map((f) => (weights[f] ? `${f}^${weights[f]}` : f))
        : fields;
}

function buildSearchQueries(state: EsState) {
    if (!state.config.search || !state.searchTerm) {
        return [];
    }

    const phrase_query = {
        multi_match: {
            type: "phrase",
            fields: weightedFields(
                state.config.search.fields,
                state.config.search.phraseBoosts
            ),
            query: state.searchTerm,
        },
    };
    const bool_prefix_query = {
        multi_match: {
            type: "bool_prefix",
            fields: weightedFields(
                state.config.search.fields,
                state.config.search.prefixBoosts
            ),
            query: state.searchTerm,
        },
    };

    if (!state.searchFuzziness) {
        return [phrase_query, bool_prefix_query];
    }

    return [
        phrase_query,
        bool_prefix_query,
        {
            multi_match: {
                fuzziness: state.searchFuzziness,
                fields: weightedFields(
                    state.config.search.fields,
                    state.config.search.fuzzyBoosts
                ),
                query: state.searchTerm,
            },
        },
    ];
}

function buildFilterQuery(
    key: string,
    config: EsFilterConfig,
    state: EsFilterState
) {
    const innerPart = () => {
        switch (config.type) {
            case "terms":
                return {
                    terms: {
                        [key]: (state as EsTermsFilterState).include,
                    },
                };
            case "range":
            case "histogram":
                return { range: { [key]: state } };
            case "date-range":
                return {
                    range: {
                        [key]: {
                            ...state,
                            format: "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ss||epoch_millis",
                        },
                    },
                };
        }
    };

    if (!config.nested) {
        return innerPart();
    }

    const path = key.substring(0, key.lastIndexOf("."));
    return {
        nested: {
            path,
            query: innerPart(),
        },
    };
}

function getFilterState(
    field: string,
    state: EsState,
    type: EsFilterConfig["type"]
): EsFilterState | undefined {
    switch (type) {
        case "terms":
            return state.terms?.[field];
        case "range":
            return state.range?.[field];
        case "histogram":
            return state.hist?.[field];
        case "date-range":
            return state.dateRange?.[field];
    }
}

function buildFilterQueries(state: EsState) {
    if (!state.config.filters) return [];

    return Object.entries(state.config.filters).reduce<Record<string, any>>(
        (acc, [key, config]) => {
            const filterState = getFilterState(key, state, config.type);
            if (filterState) {
                acc[key] = buildFilterQuery(key, config, filterState);
            }
            return acc;
        },
        {}
    );
    return Object.entries(state.config.filters)
        .map(([key, config]) => {
            const filterState = getFilterState(key, state, config.type);
            return filterState
                ? buildFilterQuery(key, config, filterState)
                : null;
        })
        .filter(Boolean) as any[];
}

function buildAggs(key: string, filter: EsFilterConfig): Record<string, any> {
    const baseAgg: Record<string, any> = (() => {
        switch (filter.type) {
            case "terms":
                return { terms: { field: key } };
            case "range":
                return {
                    range: {
                        field: key,
                        ranges: [{ from: filter.min, to: filter.max }],
                    },
                };
            case "histogram":
                return { histogram: { field: key, interval: filter.interval } };
            case "date-range":
                return {
                    date_range: {
                        field: key,
                        ranges: [{ from: "now-1M/M" }, { to: "now-1M/M" }],
                    },
                };
            default:
                return {};
        }
    })();

    if (!filter.nested) {
        return { [key]: baseAgg };
    }

    // Handle nested path
    const parts = key.split(".");
    const leafKey = parts[parts.length - 1];

    let nestedAgg: Record<string, any> = {};
    let current = nestedAgg;

    parts.forEach((part, index) => {
        if (index === parts.length - 1) {
            current[leafKey] = baseAgg;
        } else {
            current[part] = {
                nested: { path: parts.slice(0, index + 1).join(".") },
                aggs: {},
            };
            current = current[part].aggs;
        }
    });

    return nestedAgg;
}

function mergeAggs(target: any, source: any): any {
    for (const key of Object.keys(source)) {
        // If target doesn’t have this agg, copy whole subtree
        if (!target[key]) {
            target[key] = source[key];
            continue;
        }

        // Both have nested aggs → merge recursively
        if (target[key].aggs && source[key].aggs) {
            mergeAggs(target[key].aggs, source[key].aggs);
        }
    }

    return target;
}

function buildInactiveAggs(state: EsState): Record<string, any> | undefined {
    if (!state.config.filters) return undefined;

    const inactiveFilters = Object.entries(state.config.filters).filter(
        ([key, config]) => {
            const filterState = getFilterState(key, state, config.type);
            return !filterState || !(key in filterState);
        }
    );

    if (inactiveFilters.length === 0) return undefined;

    let aggs: Record<string, any> = {};

    for (const [key, config] of inactiveFilters) {
        const nestedAgg = buildAggs(key, config);
        aggs = mergeAggs(aggs, nestedAgg);
    }

    return aggs;
}

function buildSort(state: EsState) {
    return state.config.sortBy && state.sortBy
        ? state.config.sortBy[state.sortBy]
        : undefined;
}

function buildFieldIncludes(state: EsState): string[] {
    if (!state.config.columnFields) {
        return Object.entries(state.columns)
            .filter(([_, { visible }]) => visible)
            .map(([key, _]) => key);
    }
    return Object.entries(state.columns)
        .filter(([_, { visible }]) => visible)
        .flatMap(([key, _]) => state.config.columnFields?.[key] || [key]);
}

function buildQuery(must: any[], filter: any[]) {
    const bool: Record<string, any> = {};
    if (must.length > 0) bool.must = must.length === 1 ? must[0] : must;
    if (filter.length > 0)
        bool.filter = filter.length === 1 ? filter[0] : filter;
    return Object.keys(bool).length > 0 ? { bool } : { match_all: {} };
}

export function buildRequests(state: EsState): EsRequest[] {
    const searchQueries = buildSearchQueries(state);
    const activeFilterQueries = buildFilterQueries(state);

    // Main hits request
    const hitsRequest: EsRequest = {
        query: buildQuery(searchQueries, Object.values(activeFilterQueries)),
        from: (state.page - 1) * state.perPage,
        size: state.perPage,
        sort: buildSort(state),
        _source: { includes: buildFieldIncludes(state) },
        aggs: buildInactiveAggs(state),
    };

    if (!state.config.filters) return [hitsRequest];

    // Per-filter aggs requests (omit its own filter from the agg query)
    const filterAggsRequests: EsRequest[] =
        Object.entries(state.config.filters)
            .filter(([key]) =>
                Boolean(
                    getFilterState(key, state, state.config.filters![key].type)
                )
            )
            .map(([key, config]) => {
                const filtersExcludingSelf = Object.entries(activeFilterQueries)
                    .filter(([activeKey, _]) => activeKey !== key)
                    .map(([, q]) => q);

                return {
                    query: buildQuery(searchQueries, filtersExcludingSelf),
                    aggs: buildAggs(key, config),
                } as EsRequest;
            }) || [];

    return [hitsRequest, ...filterAggsRequests];
}

export function buildSelectQuery(state: EsState) {
    return state.isAllSelected
        ? buildQuery(
              buildSearchQueries(state),
              Object.values(buildFilterQueries(state))
          )
        : { ids: { values: Array.from(state.selectedIds) } };
}
