import { type LabelProps } from "@patternfly/react-core";

// Filter Configs
export interface TermsFilterConfig {
    type: "term";
    field: string;
    displayType?: "chips" | "tree";
    sizeOptions: number[];
    include?: string[] | string;
    exclude?: string[] | string;
    order?: { _count: "asc" | "desc" };
    searchable?: boolean;
    labelProps?: (bucketKey: string) => LabelProps;
    displayOrder?: string[];
}

export interface RangeFilterConfig {
    type: "range";
    field: string;
    min?: number;
    max?: number;
}

export interface HistogramFilterConfig {
    type: "histogram";
    field: string;
    interval: number;
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
    | HistogramFilterConfig
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

export interface HistogramFilterState {
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
    | HistogramFilterState
    | DateRangeFilterState
    | SearchFilterState;

export type FilterStates = Record<string, FilterState>;
