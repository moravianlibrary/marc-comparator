import {
    Fragment,
    useMemo,
    useReducer,
    useRef,
    type ReactElement,
} from "react";
import {
    InnerScrollContainer,
    OuterScrollContainer,
} from "@patternfly/react-table";
import HitsTable from "../components/organisms/HitsTable";
import {
    ActionList,
    ActionListGroup,
    ActionListItem,
    Button,
    PageGroup,
    PageSection,
    Pagination,
    Toolbar,
    ToolbarContent,
    ToolbarGroup,
    ToolbarItem,
} from "@patternfly/react-core";
import { collectionReducer } from "../store/collection/reducer";
import {
    initCollectionState,
    type CollectionConfig,
    type CollectionData,
} from "../store/collection/domain";
import { buildRequests } from "../store/collection/requests_factory";
import { buildCollectionData } from "../store/collection/data_factory";
import type { Task } from "../models/api/responses/task";
import { useSearchTasksBatch } from "../hooks/useTasks";
import type { EsHit } from "../models/api/responses/es";
import MonospaceValue from "../components/atoms/MonospaceValue";
import { Link } from "react-router";
import { CodeIcon } from "@patternfly/react-icons";
import TaskSeverityLabel from "../components/atoms/TaskSeverityLabel";
import TaskStatusLabel from "../components/atoms/TaskStatusLabel";

const CONFIG: CollectionConfig<EsHit<Task>> = {
    columns: [
        {
            key: "name",
            label: "Name",
            alwaysShow: true,
        },
        {
            key: "type",
            label: "Type",
            alwaysShow: true,
        },
        {
            key: "status",
            label: "Status",
            render: ({ _source: { status } }) => (
                <TaskStatusLabel status={status!} />
            ),
            alwaysShow: true,
        },
        {
            key: "outcome_severity",
            label: "Outcome Severity",
            render: ({ _source: { outcome_severity } }) => (
                <TaskSeverityLabel severity={outcome_severity!} />
            ),
            alwaysShow: true,
        },
        // TODO: Implement. Low priority.
        // {
        //     key: "created",
        //     label: "Created",
        //     alwaysShow: true,
        // },
        {
            key: "run_time",
            label: "Run Time",
            render: ({ _source: { started_at, finished_at } }) => {
                if (!started_at) return;

                const runTimeMs =
                    (finished_at ?? new Date()).getTime() -
                    started_at.getTime();
                const seconds = Math.floor((runTimeMs / 1000) % 60);
                const minutes = Math.floor((runTimeMs / (1000 * 60)) % 60);
                const hours = Math.floor(runTimeMs / (1000 * 60 * 60));
                return (
                    <MonospaceValue
                        value={`${hours}h ${minutes}m ${seconds}s`}
                    />
                );
            },
            alwaysShow: true,
        },
        {
            key: "traceback",
            label: "Traceback",
            render: ({ _id, _source: { status } }) => (
                <Link to={`/tasks/traceback?id=${_id}`}>
                    <Button
                        variant="plain"
                        disabled={status === "Pending"}
                        icon={<CodeIcon />}
                    />
                </Link>
            ),
            alwaysShow: true,
        },
    ],
    perPage: { options: [10, 20, 50, 100], default: 10 },
    filter: [
        {
            type: "term",
            field: "type",
            sizeOptions: [5, 10, 20],
        },
        {
            type: "term",
            field: "status",
            sizeOptions: [5, 10, 20],
        },
        {
            type: "term",
            field: "outcome_severity",
            sizeOptions: [5, 10, 20],
        },
    ],
};

const TasksTable = (): ReactElement => {
    const [state, dispatch] = useReducer(
        collectionReducer,
        initCollectionState(CONFIG)
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

    const queryResponses = useSearchTasksBatch(requests || []);

    const prevDataRef = useRef<CollectionData<Task>>({
        isLoading: true,
        isError: false,
        error: null,
        hits: [],
        totalItems: 0,
        aggregations: {},
    });
    const data: CollectionData<Task> = useMemo(() => {
        if (!queryResponses || queryResponses.length === 0) {
            return prevDataRef.current;
        }

        const newData = buildCollectionData<Task>(
            queryResponses,
            prevDataRef.current
        );

        prevDataRef.current = newData;

        return newData;
    }, [queryResponses]);

    const { config, columnStates, page, perPage } = state;

    const { isLoading, isError, error, hits, totalItems, aggregations } = data;

    const { columns } = config;

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

    return (
        <Fragment>
            <OuterScrollContainer>
                <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                    <PageSection>
                        <Toolbar collapseListedFiltersBreakpoint="lg">
                            <ToolbarContent rowWrap={{ default: "nowrap" }}>
                                <ToolbarGroup
                                    key="filters"
                                    align={{ default: "alignStart" }}
                                >
                                    <ToolbarItem></ToolbarItem>
                                </ToolbarGroup>
                            </ToolbarContent>
                        </Toolbar>
                    </PageSection>
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

export default TasksTable;
