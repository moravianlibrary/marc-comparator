import type { EsHit } from "../../models/api/responses/es";
import type { EsAggregation } from "../../models/api/responses/es_aggregations";
import type { FilterConfig, FilterStates } from "../../models/ui/filters";
import type {
    SortBy,
    TableColumnConfig,
    TableColumnState,
} from "../../models/ui/hits_table";
import type { CollectionUiPreferences } from "../../models/ui/preferences";
import type { CollectionQueryParams } from "../../models/ui/query_params";
import type { PerPageConfig, SearchConfig } from "../../models/ui/search";

export interface CollectionConfig<T> {
    columns: TableColumnConfig<T>[];
    perPage: PerPageConfig;
    search?: SearchConfig;
    filter?: FilterConfig[];
}

export interface CollectionState<T> {
    // Config
    config: CollectionConfig<T>;
    // State
    columnStates: Record<string, TableColumnState>;
    page: number;
    perPage: number;
    searchTerm?: string;
    searchFuzziness?: string;
    filterStates?: FilterStates;
    sortBy?: SortBy;
    selectedIds: Set<string>;
    isAllSelected: boolean;
}

export type CollectionAction =
    | { type: "setColumnOrder"; columnKeys: string[] }
    | { type: "toggleColumnVisibility"; columnKey: string }
    | { type: "setPaginationParams"; page: number; perPage: number }
    | { type: "setSearchTerm"; value: string }
    | { type: "toggleTerm"; field: string; bucketKey: string }
    | { type: "setRange"; field: string; from?: number; to?: number }
    | { type: "setHistogramRange"; field: string; from?: number; to?: number }
    | { type: "setDateRange"; field: string; from?: string; to?: string }
    | { type: "setFieldQuery"; field: string; query: string }
    | { type: "clearFilters"; field?: string }
    | { type: "setSortBy"; sortBy: SortBy }
    | { type: "toggleSelection"; id: string; pageIds: string[] }
    | { type: "selectPage"; pageIds: string[] }
    | { type: "selectAll" }
    | { type: "clearSelection" };

export function initCollectionState<T>(
    config: CollectionConfig<T>,
    uiPreferences?: CollectionUiPreferences,
    queryParams?: CollectionQueryParams
): CollectionState<T> {
    return {
        config,
        columnStates:
            uiPreferences?.columnStates ||
            config.columns.reduce((acc, col, index) => {
                acc[col.key] = {
                    visible: col.alwaysShow ?? col.visibleByDefault ?? false,
                    order: index,
                };
                return acc;
            }, {} as Record<string, TableColumnState>),
        page: queryParams?.page || 1,
        perPage:
            queryParams?.perPage ||
            uiPreferences?.perPage ||
            config.perPage.default,
        searchTerm: queryParams?.searchTerm,
        searchFuzziness: queryParams?.searchFuzziness,
        filterStates: queryParams?.filterStates,
        selectedIds: new Set<string>(),
        isAllSelected: false,
    };
}

export interface CollectionData<T> {
    // Results
    isLoading?: boolean;
    isError?: boolean;
    error: Error | null;
    // Parsed results
    hits?: Array<EsHit<T>>;
    totalItems?: number;
    aggregations?: Record<string, EsAggregation>;
}
