import type { ReactElement } from "react";

export interface TableColumnConfig<T> {
    key: string;
    fields?: string[];
    label: string;
    render?: (data: T) => ReactElement | null;
    visibleByDefault?: boolean;
    alwaysShow?: boolean;
}

export interface TableColumnState {
    visible: boolean;
    order: number;
}

export type SelectionType = Set<string> | "page" | "all";

export interface SortConfig {
    key: string;
    label: string;
    value: any;
    default?: boolean;
}

export interface SortBy {
    key: string;
    value: any;
}
