import type { CollectionContext } from "../../store/collection/domain";

export interface CollectionFilterProps<T> {
    field: string;
    context: CollectionContext<T>;
    placeholder?: string;
    labelRender?: (bucketKey: string) => React.ReactNode;
}
