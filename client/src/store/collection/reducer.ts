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
            return state;
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
