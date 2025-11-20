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
    Button,
    Icon,
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
import TaskSeverityLabel from "../components/atoms/TaskSeverityLabel";
import TaskStatusLabel from "../components/atoms/TaskStatusLabel";
import TermFilterCheckboxMenu from "../components/molecules/TermFilterCheckboxMenu";
import {
    TaskSeveritySchema,
    TaskStatusSchema,
    TaskTypeSchema,
} from "../models/primitives/task";
import RuntimeValue from "../components/atoms/RuntimeValue";
import DownloadTracebackButton from "../components/atoms/DonwloadTracebackButton";
import { TimesIcon } from "@patternfly/react-icons";

const TASK_TYPE_ORDER: Record<string, number> = TaskTypeSchema.options.reduce(
    (acc, type, index) => {
        acc[type] = index;
        return acc;
    },
    {} as Record<string, number>
);
const TASK_STATUS_ORDER: Record<string, number> =
    TaskStatusSchema.options.reduce((acc, status, index) => {
        acc[status] = index;
        return acc;
    }, {} as Record<string, number>);
const TASK_OUTCOME_SEVERITY_ORDER: Record<string, number> =
    TaskSeveritySchema.options.reduce((acc, severity, index) => {
        acc[severity] = index;
        return acc;
    }, {} as Record<string, number>);

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
            render: ({ _source: { started_at, finished_at } }) =>
                started_at ? (
                    <RuntimeValue
                        startedAt={started_at}
                        finishedAt={finished_at ?? null}
                    />
                ) : undefined,
            alwaysShow: true,
        },
        {
            key: "traceback",
            label: "Traceback",
            render: ({ _id, _source: { status, traceback_lines } }) => (
                <DownloadTracebackButton
                    task_id={_id}
                    status={status!}
                    traceback_lines={traceback_lines ?? null}
                />
            ),
            alwaysShow: true,
        },
        {
            key: "revoke",
            label: "Revoke",
            render: ({ _id, _source: { status } }) => (
                <Button
                    variant="plain"
                    isDanger
                    isDisabled={status !== "Pending" && status !== "Started"}
                    icon={
                        <Icon
                            status={
                                status !== "Pending" && status !== "Started"
                                    ? undefined
                                    : "danger"
                            }
                            isInline
                        >
                            <TimesIcon />
                        </Icon>
                    }
                />
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
            orderBucketBy: (a, b) =>
                TASK_TYPE_ORDER[a.key] - TASK_TYPE_ORDER[b.key],
        },
        {
            type: "term",
            field: "status",
            sizeOptions: [5, 10, 20],
            orderBucketBy: (a, b) =>
                TASK_STATUS_ORDER[a.key] - TASK_STATUS_ORDER[b.key],
        },
        {
            type: "term",
            field: "outcome_severity",
            sizeOptions: [5, 10, 20],
            orderBucketBy: (a, b) =>
                TASK_OUTCOME_SEVERITY_ORDER[a.key] -
                TASK_OUTCOME_SEVERITY_ORDER[b.key],
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

    const { isLoading, isError, error, hits, totalItems } = data;

    const context = { config, state, data, dispatch };

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
                                    <ToolbarItem>
                                        <TermFilterCheckboxMenu
                                            field="type"
                                            context={context}
                                        />
                                    </ToolbarItem>
                                    <ToolbarItem>
                                        <TermFilterCheckboxMenu
                                            field="status"
                                            context={context}
                                        />
                                    </ToolbarItem>
                                    <ToolbarItem>
                                        <TermFilterCheckboxMenu
                                            field="outcome_severity"
                                            context={context}
                                        />
                                    </ToolbarItem>
                                    {Object.keys(state.filterStates || {})
                                        .length > 0 && (
                                        <ToolbarItem>
                                            <Button
                                                variant="link"
                                                onClick={handleClearFilters}
                                            >
                                                Clear
                                            </Button>
                                        </ToolbarItem>
                                    )}
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
