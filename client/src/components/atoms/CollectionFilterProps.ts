import type { Dispatch } from "react";
import type {
    CollectionAction,
    CollectionConfig,
    CollectionData,
    CollectionState,
} from "../../store/collection/domain";

export interface CollectionFilterProps<T> {
    field: string;
    config: CollectionConfig<T>;
    state: CollectionState<T>;
    data: CollectionData<T>;
    dispatch: Dispatch<CollectionAction>;
}
