import { type CollectionData, type CollectionState } from "./domain";

export const selectSelectedCount = <T>(
    state: CollectionState<T>,
    data: CollectionData<T>
): number =>
    state.isAllSelected ? data.totalItems ?? 0 : state.selectedIds.size;
