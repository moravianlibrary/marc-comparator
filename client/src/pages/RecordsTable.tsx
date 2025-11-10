import {
    Fragment,
    useMemo,
    useReducer,
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
    Page,
    PageGroup,
    PageSection,
    Pagination,
} from "@patternfly/react-core";
import { collectionReducer } from "../store/collection/reducer";
import { initCollectionState } from "../store/collection/domain";
import { generateCatalogRecordsConfig } from "./records-table/config";
import { buildRequests } from "../store/collection/requests_factory";
import { buildCollectionData } from "../store/collection/data_factory";

const RecordsTable = (): ReactElement => {
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
        ]
    );

    const queryResponses = useSearchCatalogRecordsBatch(requests || []);

    const data = useMemo(
        () =>
            (queryResponses && buildCollectionData(queryResponses)) || {
                isLoading: true,
                isError: false,
                error: undefined,
                hits: [],
                totalItems: 0,
            },
        [queryResponses]
    );

    const { config, columnStates, page, perPage, selectedIds, isAllSelected } =
        state;

    const { isLoading, isError, error, hits, totalItems } = data;

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

    const toolbar = (
        <RecordsTableToolbar
            state={state}
            dispatch={dispatch}
            data={data}
            onShowFilters={() => setShowFilters(!showFilters)}
        />
    );

    if (showFilters) {
        return (
            <Fragment>
                <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                    <PageSection>{toolbar}</PageSection>
                </PageGroup>
                <PageGroup>
                    <PageSection></PageSection>
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
                                        Show {totalItems} Results
                                    </Button>
                                </ActionListItem>
                                <ActionListItem>
                                    <Button
                                        variant="link"
                                        onClick={() => setShowFilters(false)}
                                    >
                                        Cancel
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
                                title: "No records found",
                                body: "Try adjusting your search or filter to find what you're looking for.",
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
                                perPageSuffix: "items per page",
                                ofWord: "of",
                            }}
                        />
                    </PageSection>
                </PageGroup>
            </OuterScrollContainer>
        </Fragment>
    );
};

export default RecordsTable;
