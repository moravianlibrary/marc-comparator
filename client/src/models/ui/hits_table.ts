import type { ReactElement } from "react";
import type { UiText } from "./text";

export interface TableColumnConfig {
    key: string;
    fields?: string[];
    label: string;
    render?: (data: any) => ReactElement;
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
    label: UiText;
    value: any;
    default?: boolean;
}
