import type { EsRequest } from "../../models/api/requests/es";
import type { FilterConfig, FilterState } from "../../models/ui/filters";
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
    switch (config.type) {
        case "terms":
            return { terms: { [config.field]: state } };
        case "range":
            return {
                range: {
                    [config.field]: {
                        gte: (state as any).from,
                        lte: (state as any).to,
                    },
                },
            };
        case "histogram":
            return {
                range: {
                    [config.field]: {
                        gte: (state as any).from,
                        lte: (state as any).to,
                    },
                },
            };
        case "date-range":
            return {
                range: {
                    [config.field]: {
                        gte: (state as any).from,
                        lte: (state as any).to,
                        format: "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ss||epoch_millis",
                    },
                },
            };
        case "search":
            return {
                match: {
                    [config.field]: state as unknown as string,
                },
            };
    }
}

function buildAggs(configs: FilterConfig[]): Record<string, any> {
    return configs.reduce((acc, filter) => {
        if (filter.type === "terms") {
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
                    size: 0,
                    aggs: buildAggs([config]),
                } as EsRequest;
            }) || [];

    return [hitsRequest, ...filterAggsRequests];
}
