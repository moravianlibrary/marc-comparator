import {
    useMutation,
    useQueries,
    useQuery,
    type UseQueryResult,
} from "@tanstack/react-query";
import type { EsRequest } from "../models/api/requests/es";
import type { EsQuery } from "../models/api/requests/es_query";
import type { HideCatalogRecordsParams } from "../models/api/requests/catalog_record";
import type { SearchCatalogRecordsResponse } from "../models/api/responses/catalog_record";
import apiClient from "../services/apiClient";
import type { Task } from "../models/api/responses/task";
import { buildCollectionData } from "../store/collection/data_factory";
import {
    initCollectionState,
    type CollectionAction,
    type CollectionConfig,
    type CollectionData,
    type CollectionState,
} from "../store/collection/domain";
import {
    createContext,
    useContext,
    useMemo,
    useReducer,
    type ReactNode,
} from "react";
import { collectionReducer } from "../store/collection/reducer";
import { buildRequests } from "../store/collection/requests_factory";
import LocalizedDateTime from "../components/atoms/LocalizedDateTime";
import MonospaceValue from "../components/atoms/MonospaceValue";
import { Button } from "@patternfly/react-core";
import { DetailsIcon } from "../components/atoms/Icons";
import { Link, useNavigate } from "react-router";

// -------------------------
// Queries
// -------------------------
export const useSearchCatalogRecords = (request: EsRequest, enabled = true) =>
    useQuery<SearchCatalogRecordsResponse>({
        queryKey: ["documents", "search", request],
        queryFn: async () =>
            (await apiClient.post("/records/search", request)).data,
        enabled,
    });

export const useSearchCatalogRecordsBatch = (
    requests: EsRequest[],
    enabled = true
): UseQueryResult<SearchCatalogRecordsResponse, unknown>[] =>
    useQueries({
        queries: requests.map((request, idx) => ({
            queryKey: ["documents", "search", idx, request],
            queryFn: async () =>
                (await apiClient.post("/records/search", request)).data,
            enabled,
        })),
    });

// -------------------------
// Mutations
// -------------------------
export const useHideCatalogRecords = (
    query: EsQuery,
    params: HideCatalogRecordsParams
) =>
    useMutation<Task, Error, { query: EsQuery }>({
        mutationFn: async () =>
            (await apiClient.post("/records/hide", query, { params })).data,
    });

// -------------------------
// Config
// -------------------------
const config: CollectionConfig = {
    columns: [
        {
            key: "id",
            label: "ID",
            visibleByDefault: true,
            render: (hit) => (
                <MonospaceValue value={`${hit.base}-${hit.system_number}`} />
            ),
        },
        { key: "base", label: "Base" },
        {
            key: "system_number",
            label: "System Number",
            render: (hit) => <MonospaceValue value={hit.system_number} />,
        },
        { key: "title", label: "Title" },
        {
            key: "state",
            label: "State",
            alwaysShow: true,
        },
        {
            key: "last_sync",
            label: "Last Sync",
            visibleByDefault: true,
            render: (hit) => <LocalizedDateTime dateString={hit.last_sync} />,
        },
        {
            key: "details",
            label: "Details",
            render: (hit) => (
                <Link
                    to={`/records/details?id=${hit.base}-${hit.system_number}`}
                >
                    <Button variant="plain" icon={<DetailsIcon />} />
                </Link>
            ),
            alwaysShow: true,
        },
    ],
    perPage: { options: [10, 20, 50, 100], default: 10 },
    search: { fields: [] },
    filter: [],
    sortBy: [
        {
            key: "relevance",
            label: "common:controls.sort-by.relevance",
            value: [
                { field: "_score", order: "desc" },
                { field: "created_at", order: "desc" },
            ],
        },
    ],
    actions: [],
};

// -------------------------
// Context
// -------------------------
export interface CatalogRecordsContextType {
    state: CollectionState;
    dispatch: React.Dispatch<CollectionAction>;
    data: CollectionData;
}

const CatalogRecordsContext = createContext<
    CatalogRecordsContextType | undefined
>(undefined);

interface CatalogRecordsProviderProps {
    children: ReactNode;
}

export function CatalogRecordsProvider({
    children,
}: CatalogRecordsProviderProps) {
    const [state, dispatch] = useReducer(
        collectionReducer,
        initCollectionState(config)
    );

    const requests = useMemo(
        () => buildRequests(state),
        [
            state.page,
            state.perPage,
            state.searchTerm,
            state.searchFuzziness,
            JSON.stringify(state.filterStates),
            state.sortBy,
        ]
    );

    const queryResponses = useSearchCatalogRecordsBatch(requests);

    const data = useMemo(
        () => buildCollectionData(queryResponses),
        [queryResponses]
    );

    return (
        <CatalogRecordsContext.Provider value={{ state, dispatch, data }}>
            {children}
        </CatalogRecordsContext.Provider>
    );
}

export function useCatalogRecords() {
    const context = useContext(CatalogRecordsContext);
    if (!context)
        throw new Error(
            "useCatalogRecordsContext must be used within a CatalogRecordsProvider"
        );
    return context;
}
