import { type TermsFilterState } from "../../models/ui/filters";
import type { CollectionAction, CollectionState } from "./domain";

export function collectionReducer(
    state: CollectionState,
    action: CollectionAction
): CollectionState {
    switch (action.type) {
        case "setColumnOrder": {
            const newColumnStates = { ...state.columnStates };
            action.columnKeys.forEach((key, index) => {
                if (newColumnStates[key]) {
                    newColumnStates[key].order = index;
                }
            });
            return {
                ...state,
                columnStates: newColumnStates,
            };
        }
        case "toggleColumnVisibility": {
            const currentState = state.columnStates[action.columnKey];
            if (!currentState) {
                return state;
            }
            return {
                ...state,
                columnStates: {
                    ...state.columnStates,
                    [action.columnKey]: {
                        ...currentState,
                        visible: !currentState.visible,
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
            const filterState = state.filterStates?.[action.field] as
                | TermsFilterState
                | undefined;
            const filterConfig = state.config.filter.find(
                (f) => f.field === action.field
            );

            // Guard clauses
            if (!filterConfig || filterConfig.type !== "terms") {
                return state;
            }

            // If no filter state exists yet, create it
            if (!filterState || !filterState.include) {
                return {
                    ...state,
                    filterStates: {
                        ...state.filterStates,
                        [action.field]: {
                            include: [action.bucketKey],
                            size: filterConfig.sizeOptions?.[0] || 10,
                        },
                    },
                };
            }

            // The filter state exists, but the bucket is not included yet, add it
            if (!filterState.include.includes(action.bucketKey)) {
                return {
                    ...state,
                    filterStates: {
                        ...state.filterStates,
                        [action.field]: {
                            ...filterState,
                            include: [...filterState.include, action.bucketKey],
                        },
                    },
                };
            }

            // The bucket is already included, there are other buckets included, remove just this one
            if (filterState.include.length > 1) {
                return {
                    ...state,
                    filterStates: {
                        ...state.filterStates,
                        [action.field]: {
                            ...filterState,
                            include: filterState.include.filter(
                                (key) => key !== action.bucketKey
                            ),
                        },
                    },
                };
            }

            // The bucket is the only one included, remove the whole filter state
            const newFilterStates = { ...state.filterStates };
            delete newFilterStates[action.field];
            return {
                ...state,
                filterStates: newFilterStates,
            };
        }
        case "setHistogramRange": {
            const filterState = state.filterStates?.[action.field] as
                | { from?: number; to?: number }
                | undefined;
            const filterConfig = state.config.filter.find(
                (f) => f.field === action.field
            );

            // Guard clauses
            if (!filterConfig || filterConfig.type !== "histogram") {
                return state;
            }

            // If no filter state exists yet, create it
            if (!filterState) {
                return {
                    ...state,
                    filterStates: {
                        ...state.filterStates,
                        [action.field]: {
                            from: action.from,
                            to: action.to,
                        },
                    },
                };
            }

            // Update existing filter state
            return {
                ...state,
                filterStates: {
                    ...state.filterStates,
                    [action.field]: {
                        from: action.from,
                        to: action.to,
                    },
                },
            };
        }
        case "clearFilters": {
            if (action.field) {
                const newFilterStates = { ...state.filterStates };
                delete newFilterStates[action.field];
                return {
                    ...state,
                    filterStates: newFilterStates,
                };
            }

            return {
                ...state,
                filterStates: undefined,
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
