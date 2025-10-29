import type { TableColumnState } from "./hits_table";

export interface CollectionUiPreferences {
    // Columns
    columnStates: Record<string, TableColumnState>;
    // Pagination
    perPage: number;
    // Sorting
    sortBy: string;
}
