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

function buildFieldIncludes(
    columnConfigs: TableColumnConfig[],
    columnStates: Record<string, TableColumnState>
): string[] {
    return columnConfigs
        .filter((col) => columnStates[col.key]?.visible)
        .map((col) => col.fields || [col.key])
        .flat();
}

export function buildRequests(state: CollectionState): EsRequest[] {
    const searchQueries = state.searchTerm
        ? buildSearchQueries(
              state.config.search,
              state.searchTerm,
              state.searchFuzziness
          )
        : [];
    const filterQueries = state.config.filter
        .filter(
            (config) => state.filterStates && state.filterStates[config.field]
        )
        .reduce((acc, config) => {
            acc[config.field] = buildFilterQuery(
                config,
                state.filterStates![config.field]
            );
            return acc;
        }, {} as Record<string, any>);
    const aggs = buildAggs(state.config.filter);

    const hitsRequest: EsRequest = {
        query: { match_all: {} },
        from: (state.page - 1) * state.perPage,
        size: state.perPage,
        sort: state.sortBy?.value,
        _source: {
            includes: buildFieldIncludes(
                state.config.columns,
                state.columnStates
            ),
        },
        aggs: aggs,
    };

    return [hitsRequest];
}
