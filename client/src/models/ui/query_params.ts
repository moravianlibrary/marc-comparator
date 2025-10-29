import type { FilterStates } from "./filters";

export interface CollectionQueryParams {
    // Pagination
    page?: number;
    perPage: number;
    // Search
    searchTerm?: string;
    searchFuzziness?: string;
    // Filter
    filterStates?: FilterStates;
    // Sorting
    sortBy: string;
}
