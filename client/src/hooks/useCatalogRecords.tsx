import {
    useMutation,
    useQueries,
    useQuery,
    type UseQueryResult,
} from "@tanstack/react-query";
import type { EsRequest } from "../models/api/requests/es";
import type { EsQuery } from "../models/api/requests/es_query";
import type {
    AddBatchOfRecordsData,
    AddOneRecordData,
    HideCatalogRecordsParams,
    SetHiddenStateData,
    SyncRecordsData,
} from "../models/api/requests/catalog_record";
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
    useState,
    type ReactNode,
} from "react";
import { collectionReducer } from "../store/collection/reducer";
import { buildRequests } from "../store/collection/requests_factory";
import LocalizedDateTime from "../components/atoms/LocalizedDateTime";
import MonospaceValue from "../components/atoms/MonospaceValue";
import { Button, Label, LabelGroup } from "@patternfly/react-core";
import { DetailsIcon } from "../components/atoms/Icons";
import { Link, useNavigate } from "react-router";
import type { CatalogRecordState } from "../models/primitives/catalog_record";
import MarcTitle from "../components/atoms/MarcTitle";
import { useGetSystemInfo } from "./useSystem";
import {
    selectSelectedCount,
    selectSelectionQuery,
} from "../store/collection/selectors";
import { useLinkToAuthorities } from "./useAuthorityLinking";

// -------------------------
// Queries
// -------------------------
export const useSearchCatalogRecords = (request: EsRequest, enabled = true) =>
    useQuery<SearchCatalogRecordsResponse>({
        queryKey: ["catalog-records", "search", request],
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
            queryKey: ["catalog-records", "search", idx, request],
            queryFn: async () =>
                (await apiClient.post("/records/search", request)).data,
            enabled,
        })),
    });

export const useGetAvailableTargetBases = () =>
    useQuery<string[]>({
        queryKey: ["catalog-records", "search", "available-target-bases"],
        queryFn: async () =>
            (
                (
                    await apiClient.post("/records/search", {
                        query: {
                            size: 0,
                            aggs: {
                                distinct_authority_bases: {
                                    nested: {
                                        path: "authority_links",
                                    },
                                    aggs: {
                                        bases: {
                                            terms: {
                                                field: "authority_links.base.keyword",
                                                size: 100,
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    })
                ).data.aggregations?.distinct_authority_bases?.bases?.buckets ??
                []
            ).map((bucket: { key: string }) => bucket.key),
    });

// -------------------------
// Mutations
// -------------------------
export const useAddOneRecord = () =>
    useMutation<Task, Error, AddOneRecordData>({
        mutationFn: async (data: AddOneRecordData) =>
            (await apiClient.post("/records/fetch", data)).data,
    });

export const useAddBatchOfRecords = () =>
    useMutation<Task, Error, AddBatchOfRecordsData>({
        mutationFn: async (data: AddBatchOfRecordsData) =>
            (await apiClient.post("/records/fetch-batch", data)).data,
    });

export const useSyncRecords = () =>
    useMutation<Task, Error, SyncRecordsData>({
        mutationFn: async (data: SyncRecordsData) =>
            (await apiClient.post("/records/sync", data)).data,
    });

export const useReindexRecords = () =>
    useMutation<Task, Error, EsQuery>({
        mutationFn: async (data: EsQuery) =>
            (await apiClient.post("/records/reindex", data)).data,
    });

export const useSetHiddenStateOfRecords = () =>
    useMutation<Task, Error, SetHiddenStateData>({
        mutationFn: async (data) =>
            (await apiClient.post("/records/hide", data)).data,
    });

// TODO: Remove!
// -------------------------
// Config
// -------------------------
const STATE_RANKING: Record<CatalogRecordState, number> = {
    Active: 1,
    Deleted: 2,
    Valid: 3,
    Invalid: 4,
    Hidden: 5,
};
const STATE_COLOR_MAP: Record<
    CatalogRecordState,
    "yellow" | "grey" | "green" | "red" | "blue"
> = {
    Active: "yellow",
    Deleted: "grey",
    Valid: "green",
    Invalid: "red",
    Hidden: "blue",
};
const COLUMNS_CONFIG = [
    {
        key: "id",
        label: "ID",
        visibleByDefault: true,
        render: (hit) => (
            <MonospaceValue value={`${hit.base}-${hit.system_number}`} />
        ),
    },
    {
        key: "base",
        label: "Base",
        render: (hit) => <MonospaceValue value={hit.base} />,
    },
    {
        key: "system_number",
        label: "System Number",
        render: (hit) => <MonospaceValue value={hit.system_number} />,
    },
    {
        key: "title",
        label: "Title",
        render: (hit) => (
            <MarcTitle title={hit.title} subtitle={hit.subtitle} />
        ),
    },
    {
        key: "state",
        label: "State",
        alwaysShow: true,
        render: (hit) => (
            <LabelGroup>
                {hit.state
                    .sort((a, b) => STATE_RANKING[a] - STATE_RANKING[b])
                    .map((state: CatalogRecordState, index: number) => (
                        <Label key={index} color={STATE_COLOR_MAP[state]}>
                            {state}
                        </Label>
                    ))}
            </LabelGroup>
        ),
    },
    {
        key: "authority_links",
        label: "Authority Links",
        visibleByDefault: true,
        render: (hit) => (
            <LabelGroup>
                {hit.authority_links.map(
                    (link: { base: string }, index: number) => (
                        <Label key={index}>{link.base}</Label>
                    )
                )}
            </LabelGroup>
        ),
    },
    {
        key: "comparisons",
        label: "Comparisons",
        visibleByDefault: true,
        render: (hit) => (
            <LabelGroup>
                {hit.comparisons.map(
                    (
                        c: {
                            base: string;
                            comparator: string;
                            overall_score: number;
                        },
                        index: number
                    ) => (
                        <Label key={index}>
                            {c.base} {c.comparator}: {c.overall_score}
                        </Label>
                    )
                )}
            </LabelGroup>
        ),
    },
    {
        key: "latest_sync",
        label: "Last Sync",
        visibleByDefault: true,
        render: (hit) => <LocalizedDateTime dateString={hit.latest_sync} />,
    },
    {
        key: "details",
        label: "Details",
        render: (hit) => (
            <Link to={`/records/details?id=${hit.base}-${hit.system_number}`}>
                <Button variant="plain" icon={<DetailsIcon />} />
            </Link>
        ),
        alwaysShow: true,
    },
];

const config: CollectionConfig = {
    columns: COLUMNS_CONFIG,
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
    actions: [
        {
            label: "Run Authority Linking",
            icon: <></>,
            onClick: () => {},
        },
        {
            label: "Run Comparisons",
            icon: <></>,
            onClick: () => {},
        },
        {
            label: "Run Validations",
            icon: <></>,
            onClick: () => {},
        },
        {
            label: "Hide Records",
            icon: <></>,
            onClick: () => {},
        },
        {
            label: "Unhide Records",
            icon: <></>,
            onClick: () => {},
        },
        {
            label: "Reindex Records",
            icon: <></>,
            onClick: () => {},
        },
    ],
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
    const { data: systemInfo, isLoading: isSystemInfoLoading } =
        useGetSystemInfo();

    const authorityLinkers = systemInfo?.enabled_authority_linkers ?? [];
    const authorityLinkingMutation = useLinkToAuthorities();
    const [isLinkRecordsModalOpen, setLinkRecordsModalOpen] =
        useState<boolean>(false);
    const handleAuthorityLinking = (targetBase: string, linkers: string[]) => {
        authorityLinkingMutation.mutate({
            target_base: targetBase,
            linkers: linkers,
            query: selectSelectionQuery(state),
        });
        setLinkRecordsModalOpen(false);
    };

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
