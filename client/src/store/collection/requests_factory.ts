import type { EsRequest } from "../../models/api/requests/es";
import type {
    DateRangeFilterState,
    FilterConfig,
    FilterState,
    HistogramFilterState,
    RangeFilterState,
    SearchFilterState,
    TermsFilterState,
} from "../../models/ui/filters";
import type {
    TableColumnConfig,
    TableColumnState,
} from "../../models/ui/hits_table";
import type { SearchConfig } from "../../models/ui/search";
import type { CollectionState } from "./domain";

function weightedFields(
    fields: string[],
    weights: Record<string, number> | undefined
): string[] {
    return weights
        ? fields.map((f) => (weights[f] ? `${f}^${weights[f]}` : f))
        : fields;
}

function buildSearchQueries(
    config: SearchConfig,
    term: string,
    fuzziness?: string
) {
    const phrase_query = {
        multi_match: {
            type: "phrase",
            fields: weightedFields(config.fields, config.phraseBoosts),
            query: term,
        },
    };
    const bool_prefix_query = {
        multi_match: {
            type: "bool_prefix",
            fields: weightedFields(config.fields, config.prefixBoosts),
            query: term,
        },
    };

    if (!fuzziness) {
        return [phrase_query, bool_prefix_query];
    }

    return [
        phrase_query,
        bool_prefix_query,
        {
            multi_match: {
                fuzziness: fuzziness,
                fields: weightedFields(config.fields, config.fuzzyBoosts),
                query: term,
            },
        },
    ];
}

function buildFilterQuery(config: FilterConfig, state: FilterState) {
    console.log("buildFilterQuery", config, state);
    switch (config.type) {
        case "term":
            return {
                terms: { [config.field]: (state as TermsFilterState).include },
            };
        case "range":
        case "histogram":
            const { from, to } = state as
                | RangeFilterState
                | HistogramFilterState;
            return {
                range: {
                    [config.field]: {
                        ...(from !== undefined ? { gte: from } : {}),
                        ...(to !== undefined ? { lte: to } : {}),
                    },
                },
            };
        case "date-range":
            const dateState = state as DateRangeFilterState;
            return {
                range: {
                    [config.field]: {
                        ...(dateState.from ? { gte: dateState.from } : {}),
                        ...(dateState.to ? { lte: dateState.to } : {}),
                        format: "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ss||epoch_millis",
                    },
                },
            };
        case "search":
            const searchState = state as SearchFilterState;
            return { match: { [config.field]: searchState.value } };
    }
}

function buildAggs(configs: FilterConfig[]): Record<string, any> {
    return configs.reduce((acc, filter) => {
        if (filter.type === "term") {
            acc[filter.field] = { terms: { field: filter.field } };
        } else if (filter.type === "range") {
            acc[filter.field] = {
                range: {
                    field: filter.field,
                    ranges: [{ from: filter.min, to: filter.max }],
                },
            };
        } else if (filter.type === "histogram") {
            acc[filter.field] = {
                histogram: {
                    field: filter.field,
                    interval: filter.interval,
                },
            };
        } else if (filter.type === "date-range") {
            acc[filter.field] = {
                date_range: {
                    field: filter.field,
                    // TODO: make ranges configurable
                    ranges: [
                        {
                            from: "2018-01-01T00:00:00Z",
                            to: "2019-01-01T00:00:00Z",
                        },
                        {
                            from: "2019-01-01T00:00:00Z",
                            to: "2020-01-01T00:00:00Z",
                        },
                        {
                            from: "2021-01-01T00:00:00Z",
                            to: "2022-01-01T00:00:00Z",
                        },
                        {
                            from: "2022-01-01T00:00:00Z",
                            to: "2023-01-01T00:00:00Z",
                        },
                        {
                            from: "2023-01-01T00:00:00Z",
                            to: "2024-01-01T00:00:00Z",
                        },
                        {
                            from: "2024-01-01T00:00:00Z",
                            to: "2025-01-01T00:00:00Z",
                        },
                        { from: "2025-01-01T00:00:00Z" },
                    ],
                    // ranges: [{ min: filter., max: filter.max }],
                },
            };
        }
        return acc;
    }, {} as Record<string, any>);
}

function buildFieldIncludes<T>(
    columnConfigs: TableColumnConfig<T>[],
    columnStates: Record<string, TableColumnState>
): string[] {
    return columnConfigs
        .filter((col) => columnStates[col.key]?.visible)
        .map((col) => col.fields || [col.key])
        .flat();
}

export function buildRequests<T>(state: CollectionState<T>): EsRequest[] {
    const searchQueries =
        state.config.search && state.searchTerm
            ? buildSearchQueries(
                  state.config.search,
                  state.searchTerm,
                  state.searchFuzziness
              )
            : [];

    const activeFilterQueries: Record<string, any> = {};
    state.config.filter?.forEach((config) => {
        const filterState = state.filterStates?.[config.field];
        if (filterState) {
            activeFilterQueries[config.field] = buildFilterQuery(
                config,
                filterState
            );
        }
    });

    const buildBoolQuery = (must: any[], filter: any[]) => {
        const bool: Record<string, any> = {};
        if (must.length > 0) bool.must = must.length === 1 ? must[0] : must;
        if (filter.length > 0)
            bool.filter = filter.length === 1 ? filter[0] : filter;
        return Object.keys(bool).length > 0 ? { bool } : { match_all: {} };
    };

    // Main hits request
    const hitsRequest: EsRequest = {
        query: buildBoolQuery(
            searchQueries,
            Object.values(activeFilterQueries)
        ),
        from: (state.page - 1) * state.perPage,
        size: state.perPage,
        sort: state.sortBy?.value,
        _source: {
            includes: buildFieldIncludes(
                state.config.columns,
                state.columnStates
            ),
        },
        aggs: state.config.filter ? buildAggs(state.config.filter) : undefined,
    };

    // Per-filter aggs requests (omit its own filter from the agg query)
    const filterAggsRequests: EsRequest[] =
        state.config.filter
            ?.filter((config) => activeFilterQueries[config.field])
            .map((config) => {
                const filtersExcludingSelf = Object.entries(activeFilterQueries)
                    .filter(([field]) => field !== config.field)
                    .map(([, q]) => q);

                return {
                    query: buildBoolQuery(searchQueries, filtersExcludingSelf),
                    aggs: buildAggs([config]),
                } as EsRequest;
            }) || [];

    return [hitsRequest, ...filterAggsRequests];
}
