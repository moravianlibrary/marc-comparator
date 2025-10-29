// Filter Configs
export interface TermsFilterConfig {
    type: "terms";
    field: string;
    displayType?: "labels" | "tree";
    size?: number;
    sizeOptions?: number[];
    include?: string[] | string;
    exclude?: string[] | string;
    order?: { _count: "asc" | "desc" };
    searchable?: boolean;
    renderBucketKey?: (key: string) => React.ReactNode;
    displayOrder?: string[];
}

export interface RangeFilterConfig {
    type: "range";
    field: string;
    min?: number;
    max?: number;
}

export interface DateRangeFilterConfig {
    type: "date-range";
    field: string;
}

export interface SearchFilterConfig {
    type: "search";
    field: string;
}

export type FilterConfig =
    | TermsFilterConfig
    | RangeFilterConfig
    | DateRangeFilterConfig
    | SearchFilterConfig;

// Filter States
export interface TermsFilterState {
    size: number;
    include: string[];
}

export interface RangeFilterState {
    from?: number;
    to?: number;
}

export interface DateRangeFilterState {
    from?: string | number;
    to?: string | number;
}

export interface SearchFilterState {
    value: string;
}

export type FilterState =
    | TermsFilterState
    | RangeFilterState
    | DateRangeFilterState
    | SearchFilterState;

export type FilterStates = Record<string, FilterState>;
