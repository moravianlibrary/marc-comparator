import {
    Fragment,
    useMemo,
    useReducer,
    useRef,
    useState,
    type ReactElement,
} from "react";
import { useSearchCatalogRecordsBatch } from "../hooks/useCatalogRecords";
import {
    InnerScrollContainer,
    OuterScrollContainer,
} from "@patternfly/react-table";
import RecordsTableToolbar from "./records-table/Toolbar";
import HitsTable from "../components/organisms/HitsTable";
import {
    ActionList,
    ActionListGroup,
    ActionListItem,
    Button,
    PageGroup,
    PageSection,
    Pagination,
} from "@patternfly/react-core";
import { collectionReducer } from "../store/collection/reducer";
import {
    initCollectionState,
    type CollectionData,
} from "../store/collection/domain";
import { generateCatalogRecordsConfig } from "./records-table/config";
import { buildRequests } from "../store/collection/requests_factory";
import { buildCollectionData } from "../store/collection/data_factory";
import RecordsTableFilters from "./records-table/Filters";
import type { CatalogRecord } from "../models/api/responses/catalog_record";
import { useTranslation } from "react-i18next";

const RecordsTable = (): ReactElement => {
    const { t } = useTranslation();
    const [state, dispatch] = useReducer(
        collectionReducer,
        initCollectionState(generateCatalogRecordsConfig())
    );

    const requests = useMemo(
        () => state.sortBy && buildRequests(state),
        [
            state.page,
            state.perPage,
            state.searchTerm,
            state.searchFuzziness,
            JSON.stringify(state.filterStates),
            state.sortBy,
            JSON.stringify(state.columnStates),
        ]
    );

    const queryResponses = useSearchCatalogRecordsBatch(requests || []);

    const prevDataRef = useRef<CollectionData<CatalogRecord>>({
        isLoading: true,
        isError: false,
        error: null,
        hits: [],
        totalItems: 0,
        aggregations: {},
    });
    const data: CollectionData<CatalogRecord> = useMemo(() => {
        if (!queryResponses || queryResponses.length === 0) {
            return prevDataRef.current;
        }

        const newData = buildCollectionData<CatalogRecord>(
            queryResponses,
            prevDataRef.current
        );

        prevDataRef.current = newData;

        return newData;
    }, [queryResponses]);

    const { config, columnStates, page, perPage, selectedIds, isAllSelected } =
        state;

    const { isLoading, isError, error, hits, totalItems, aggregations } = data;

    const { columns } = config;

    const pageIds = hits?.map((hit) => hit._id) || [];

    const [showFilters, setShowFilters] = useState<boolean>(false);

    const handlePaginationChange = (newPage: number, newPerPage?: number) => {
        dispatch({
            type: "setPaginationParams",
            page: newPage,
            perPage: newPerPage || perPage || 0,
        });
    };

    const handleClearFilters = () => {
        dispatch({ type: "clearFilters" });
    };

    const toolbar = (
        <RecordsTableToolbar
            state={state}
            dispatch={dispatch}
            data={data}
            showFilters={showFilters}
            onToggleShowFilters={() => setShowFilters(!showFilters)}
        />
    );

    if (showFilters) {
        return (
            <Fragment>
                <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                    <PageSection>{toolbar}</PageSection>
                </PageGroup>
                <PageGroup>
                    <PageSection>
                        <RecordsTableFilters
                            state={state}
                            dispatch={dispatch}
                            aggregations={aggregations || {}}
                        />
                    </PageSection>
                </PageGroup>
                <PageGroup stickyOnBreakpoint={{ default: "bottom" }}>
                    <PageSection>
                        <ActionList>
                            <ActionListGroup>
                                <ActionListItem>
                                    <Button
                                        variant="primary"
                                        onClick={() => setShowFilters(false)}
                                    >
                                        {t("records:filters.apply-filters", {
                                            count: totalItems,
                                        })}
                                    </Button>
                                </ActionListItem>
                                <ActionListItem>
                                    <Button
                                        variant="link"
                                        onClick={handleClearFilters}
                                    >
                                        {t("records:filters.clear-all")}
                                    </Button>
                                </ActionListItem>
                            </ActionListGroup>
                        </ActionList>
                    </PageSection>
                </PageGroup>
            </Fragment>
        );
    }

    return (
        <Fragment>
            <OuterScrollContainer>
                <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                    <PageSection>{toolbar}</PageSection>
                </PageGroup>
                <InnerScrollContainer
                    style={{
                        marginLeft: 20,
                        marginRight: 20,
                        marginTop: 10,
                        marginBottom: 10,
                    }}
                >
                    <HitsTable
                        columns={columns}
                        columnStates={columnStates}
                        isLoading={isLoading}
                        isError={isError}
                        error={error}
                        hits={hits}
                        selectedIds={
                            isAllSelected ? new Set(pageIds) : selectedIds
                        }
                        onToggleSelect={(id) =>
                            dispatch({
                                type: "toggleSelection",
                                id,
                                pageIds,
                            })
                        }
                        onColumnOrderChange={(columnKeys) =>
                            dispatch({
                                type: "setColumnOrder",
                                columnKeys,
                            })
                        }
                        onColumnVisibilityToggle={(columnKey) =>
                            dispatch({
                                type: "toggleColumnVisibility",
                                columnKey,
                            })
                        }
                        texts={{
                            noMatchFound: {
                                title: t("records:statement.no-records-found"),
                                body: t(
                                    "records:statement.no-records-found-body"
                                ),
                            },
                        }}
                    />
                </InnerScrollContainer>
                <PageGroup stickyOnBreakpoint={{ default: "bottom" }}>
                    <PageSection>
                        <Pagination
                            style={{ marginLeft: 20, marginRight: 20 }}
                            perPageOptions={config.perPage.options.map((o) => ({
                                value: o,
                                title: o.toString(),
                            }))}
                            itemCount={totalItems}
                            page={page}
                            perPage={perPage}
                            onSetPage={(_event, newPage, newPerPage) =>
                                handlePaginationChange(newPage, newPerPage)
                            }
                            onPerPageSelect={(_event, newPerPage, newPage) =>
                                handlePaginationChange(newPage, newPerPage)
                            }
                            variant="bottom"
                            titles={{
                                perPageSuffix: t(
                                    "records:pagination.per-page-suffix"
                                ),
                                ofWord: t("records:pagination.of-word"),
                            }}
                        />
                    </PageSection>
                </PageGroup>
            </OuterScrollContainer>
        </Fragment>
    );
};

export default RecordsTable;
