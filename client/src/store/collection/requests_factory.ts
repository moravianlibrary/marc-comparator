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
    const innerPart = () => {
        switch (config.type) {
            case "term":
                return {
                    terms: {
                        [config.field]: (state as TermsFilterState).include,
                    },
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
    };

    if (!config.isNested) {
        return innerPart();
    }

    const path = config.field.substring(0, config.field.lastIndexOf("."));
    return {
        nested: {
            path,
            query: innerPart(),
        },
    };
}

function buildAggs(configs: FilterConfig[]): Record<string, any> {
    const aggs: Record<string, any> = {};

    for (const filter of configs) {
        const baseAgg: Record<string, any> = (() => {
            switch (filter.type) {
                case "term":
                    return { terms: { field: filter.field } };
                case "range":
                    return {
                        range: {
                            field: filter.field,
                            ranges: [{ from: filter.min, to: filter.max }],
                        },
                    };
                case "histogram":
                    return {
                        histogram: {
                            field: filter.field,
                            interval: filter.interval,
                        },
                    };
                case "date-range":
                    return {
                        date_range: {
                            field: filter.field,
                            ranges: [{ from: "now-1M/M" }, { to: "now-1M/M" }],
                        },
                    };
                default:
                    return {};
            }
        })();

        if (filter.isNested) {
            // Split nested path
            const parts = filter.field.split(".");
            let currentAgg = aggs;

            for (let i = 0; i < parts.length - 1; i++) {
                const path = parts.slice(0, i + 1).join(".");
                if (!currentAgg[parts[i]]) {
                    currentAgg[parts[i]] = { nested: { path }, aggs: {} };
                }
                currentAgg = currentAgg[parts[i]].aggs;
            }

            // Assign the actual aggregation at the deepest level
            currentAgg[parts[parts.length - 1]] = baseAgg;
        } else {
            aggs[filter.field] = baseAgg;
        }
    }

    return aggs;
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

function buildQuery(must: any[], filter: any[]) {
    const bool: Record<string, any> = {};
    if (must.length > 0) bool.must = must.length === 1 ? must[0] : must;
    if (filter.length > 0)
        bool.filter = filter.length === 1 ? filter[0] : filter;
    return Object.keys(bool).length > 0 ? { bool } : { match_all: {} };
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

    // Main hits request
    const hitsRequest: EsRequest = {
        query: buildQuery(searchQueries, Object.values(activeFilterQueries)),
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
                    query: buildQuery(searchQueries, filtersExcludingSelf),
                    aggs: buildAggs([config]),
                } as EsRequest;
            }) || [];

    return [hitsRequest, ...filterAggsRequests];
}

export function buildSelectQuery(state: CollectionState<any>) {
    if (!state.isAllSelected) {
        return { ids: { values: Array.from(state.selectedIds) } };
    }

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

    return buildQuery(searchQueries, Object.values(activeFilterQueries));
}
