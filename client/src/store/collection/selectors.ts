import { type EsQuery } from "../../models/api/requests/es_query";
import { type CollectionData, type CollectionState } from "./domain";

export const selectSelectedCount = (
    state: CollectionState,
    data: CollectionData<any>
): number =>
    state.isAllSelected ? data.totalItems ?? 0 : state.selectedIds.size;

export const selectSelectionQuery = (state: CollectionState): EsQuery => {
    if (state.isAllSelected) {
        return {};
    }

    return { ids: { values: Array.from(state.selectedIds) } };
};
