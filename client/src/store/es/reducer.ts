import type { TermsFilterState } from "../../models/ui/filters";
import type { EsState, EsStateAction, EsTermsFilterState } from "./domain";

export function esStateReducer(state: EsState, action: EsStateAction): EsState {
    switch (action.type) {
        case "setColumnOrder": {
            const visibleLookup: Record<string, boolean> = Object.entries(
                state.columns
            ).reduce((acc, [key, { visible }]) => {
                acc[key] = visible;
                return acc;
            }, {} as Record<string, boolean>);

            return {
                ...state,
                columns: action.columnKeys.reduce((acc, key, index) => {
                    acc[key] = {
                        order: index,
                        visible: visibleLookup[key] ?? false,
                    };
                    return acc;
                }, {} as Record<string, { order: number; visible: boolean }>),
            };
        }
        case "toggleColumnVisibility": {
            if (!(action.columnKey in state.columns)) return state;

            return {
                ...state,
                columns: {
                    ...state.columns,
                    [action.columnKey]: {
                        ...state.columns[action.columnKey],
                        visible: !state.columns[action.columnKey].visible,
                    },
                },
            };
        }
        case "setPaginationParams":
            return {
                ...state,
                page: action.page,
                perPage: action.perPage,
                selectedIds: new Set<string>(),
            };
        case "setSearchTerm":
            return {
                ...state,
                searchTerm: action.value,
                page: 1,
            };
        case "toggleTerm": {
            const filter = state.terms?.[action.field] as
                | TermsFilterState
                | undefined;
            const config = state.config.filters?.[action.field];

            // Guard clauses
            if (!config || config.type !== "terms") {
                return state;
            }

            // If no filter state exists yet, create it
            if (!filter || !filter.include) {
                return {
                    ...state,
                    terms: {
                        ...state.terms,
                        [action.field]: {
                            include: [action.bucketKey],
                            size: config.size,
                        },
                    },
                };
            }

            // The filter state exists, but the bucket is not included yet, add it
            if (!filter.include.includes(action.bucketKey)) {
                return {
                    ...state,
                    terms: {
                        ...state.terms,
                        [action.field]: {
                            ...filter,
                            include: [...filter.include, action.bucketKey],
                        },
                    },
                };
            }

            // The bucket is already included, there are other buckets included, remove just this one
            if (filter.include.length > 1) {
                return {
                    ...state,
                    terms: {
                        ...state.terms,
                        [action.field]: {
                            ...filter,
                            include: filter.include.filter(
                                (key) => key !== action.bucketKey
                            ),
                        },
                    },
                };
            }

            // The bucket is the only one included, remove the whole filter state
            const newFilters = { ...state.terms };
            delete newFilters[action.field];
            return {
                ...state,
                terms: newFilters,
            };
        }
        case "changeTermBucketSize": {
            const filter = state.terms?.[action.field] as
                | EsTermsFilterState
                | undefined;
            const config = state.config.filters?.[action.field];

            // Guard clauses
            if (!filter || !config || config.type !== "terms") {
                return state;
            }

            return {
                ...state,
                terms: {
                    ...state.terms,
                    [action.field]: {
                        ...filter,
                        size: action.size,
                    },
                },
            };
        }
        case "setHistogramRange": {
            const config = state.config.filters?.[action.field];

            // Guard clauses
            if (!config || config.type !== "histogram") {
                return state;
            }

            if (!action.gte && !action.lte) {
                // Clear the filter if no range is set
                const newFilters = { ...state.hist };
                delete newFilters[action.field];
                return {
                    ...state,
                    hist: newFilters,
                };
            }

            if (action.gte === config.min && action.lte === config.max) {
                // Clear the filter if the range matches the full extent
                const newFilters = { ...state.hist };
                delete newFilters[action.field];
                return {
                    ...state,
                    hist: newFilters,
                };
            }

            // Create new or update existing filter state
            return {
                ...state,
                hist: {
                    ...state.hist,
                    [action.field]: { gte: action.gte, lte: action.lte },
                },
            };
        }
        case "clearFilters": {
            if (action.field) {
                const config = state.config.filters?.[action.field];

                if (!config) return state;

                if (config.type === "terms") {
                    const newFilters = { ...state.terms };
                    delete newFilters[action.field];
                    return {
                        ...state,
                        terms: newFilters,
                    };
                }

                if (config.type === "range") {
                    const newFilters = { ...state.range };
                    delete newFilters[action.field];
                    return {
                        ...state,
                        range: newFilters,
                    };
                }

                if (config.type === "histogram") {
                    const newFilters = { ...state.hist };
                    delete newFilters[action.field];
                    return {
                        ...state,
                        hist: newFilters,
                    };
                }

                if (config.type === "date-range") {
                    const newFilters = { ...state.dateRange };
                    delete newFilters[action.field];
                    return {
                        ...state,
                        dateRange: newFilters,
                    };
                }
            }

            return {
                ...state,
                terms: undefined,
                range: undefined,
                hist: undefined,
                dateRange: undefined,
            };
        }
        case "setSortBy": {
            return {
                ...state,
                sortBy: action.sortBy,
            };
        }
        case "toggleSelection": {
            const { id, pageIds } = action;

            if (state.isAllSelected) {
                const newSelected = new Set(
                    pageIds.filter((_id) => _id !== id)
                );
                return {
                    ...state,
                    selectedIds: newSelected,
                    isAllSelected: false,
                };
            }

            const newSelected = new Set(state.selectedIds);
            if (newSelected.has(id)) {
                newSelected.delete(id);
            } else {
                newSelected.add(id);
            }

            return {
                ...state,
                selectedIds: newSelected,
            };
        }
        case "selectPage": {
            return {
                ...state,
                selectedIds: new Set(action.pageIds),
                isAllSelected: false,
            };
        }
        case "selectAll": {
            return {
                ...state,
                selectedIds: new Set<string>(),
                isAllSelected: true,
            };
        }
        case "clearSelection": {
            return {
                ...state,
                selectedIds: new Set<string>(),
                isAllSelected: false,
            };
        }
    }
    return state;
}
