import { useMemo, useReducer, useRef, type ReactElement } from "react";
import {
    InnerScrollContainer,
    OuterScrollContainer,
} from "@patternfly/react-table";
import HitsTable from "../components/organisms/HitsTable";
import {
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
import TaskSeverityLabel from "../components/tasks/atoms/TaskSeverityLabel";
import TaskStatusLabel from "../components/tasks/atoms/TaskStatusLabel";
import TermFilterCheckboxMenu from "../components/molecules/TermFilterCheckboxMenu";
import {
    TaskSeveritySchema,
    TaskStatusSchema,
    TaskTypeSchema,
    type TaskSeverity,
    type TaskStatus,
    type TaskType,
} from "../models/primitives/task";
import RuntimeValue from "../components/atoms/RuntimeValue";
import { useGetMe } from "../hooks/useAuth";
import type { EsTermsBucket } from "../models/api/responses/es_aggregations";
import { useTranslation } from "react-i18next";
import RevokeTaskButton from "../components/tasks/atoms/RevokeButton";
import ShowTaskDetailsButton from "../components/tasks/atoms/ShowDetailsButton";
import TaskName from "../components/tasks/atoms/TaskName";
import TaskTypeText from "../components/tasks/atoms/TaskTypeText";

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

const generateConfig = (): CollectionConfig<EsHit<Task>> => {
    const { t } = useTranslation("tasks");
    return {
        columns: [
            {
                key: "name",
                label: t("fields.name"),
                alwaysShow: true,
                render: (hit) => <TaskName hit={hit} />,
            },
            {
                key: "type",
                label: t("fields.type"),
                alwaysShow: true,
                render: (hit) => <TaskTypeText hit={hit} />,
            },
            {
                key: "status",
                label: t("fields.status"),
                render: ({ _source: { status } }) => (
                    <TaskStatusLabel status={status!} />
                ),
                alwaysShow: true,
            },
            {
                key: "outcome_severity",
                label: t("fields.severity"),
                render: ({ _source: { outcome_severity } }) => (
                    <TaskSeverityLabel severity={outcome_severity!} />
                ),
                alwaysShow: true,
            },
            {
                key: "run_time",
                fields: ["started_at", "finished_at"],
                label: t("fields.run-time"),
                render: ({ _source: { started_at, finished_at } }) =>
                    started_at ? (
                        <RuntimeValue
                            startedAt={started_at}
                            finishedAt={finished_at ?? null}
                        />
                    ) : null,
                alwaysShow: true,
            },
            {
                key: "details",
                label: t("fields.details"),
                render: (hit) => <ShowTaskDetailsButton hit={hit} />,
                alwaysShow: true,
            },
            {
                key: "revoke",
                label: t("fields.revoke"),
                render: ({ _id, _source: { status } }) => (
                    <RevokeTaskButton _id={_id} status={status!} />
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
                    TASK_TYPE_ORDER[(a as EsTermsBucket).key] -
                    TASK_TYPE_ORDER[(b as EsTermsBucket).key],
            },
            {
                type: "term",
                field: "status",
                sizeOptions: [5, 10, 20],
                orderBucketBy: (a, b) =>
                    TASK_STATUS_ORDER[(a as EsTermsBucket).key] -
                    TASK_STATUS_ORDER[(b as EsTermsBucket).key],
            },
            {
                type: "term",
                field: "outcome_severity",
                sizeOptions: [5, 10, 20],
                orderBucketBy: (a, b) =>
                    TASK_OUTCOME_SEVERITY_ORDER[(a as EsTermsBucket).key] -
                    TASK_OUTCOME_SEVERITY_ORDER[(b as EsTermsBucket).key],
            },
        ],
        sortBy: { created_at: { order: "desc" } },
    };
};

const TasksTable = (): ReactElement => {
    const { t } = useTranslation("tasks");

    const [state, dispatch] = useReducer(
        collectionReducer,
        initCollectionState(generateConfig())
    );
    const { data: me } = useGetMe();

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

    const queryResponses = useSearchTasksBatch(
        requests || [],
        !!me,
        me?.permissions.includes("ManageTasks") ? "all" : "own"
    );

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
                                        placeholder={t(
                                            "filters.type-placeholder"
                                        )}
                                        labelRender={(type) => (
                                            <TaskTypeText
                                                type={type as TaskType}
                                            />
                                        )}
                                    />
                                </ToolbarItem>
                                <ToolbarItem>
                                    <TermFilterCheckboxMenu
                                        field="status"
                                        context={context}
                                        placeholder={t(
                                            "filters.status-placeholder"
                                        )}
                                        labelRender={(status) => (
                                            <TaskStatusLabel
                                                status={status as TaskStatus}
                                            />
                                        )}
                                    />
                                </ToolbarItem>
                                <ToolbarItem>
                                    <TermFilterCheckboxMenu
                                        field="outcome_severity"
                                        context={context}
                                        placeholder={t(
                                            "filters.severity-placeholder"
                                        )}
                                        labelRender={(severity) => (
                                            <TaskSeverityLabel
                                                severity={
                                                    severity as TaskSeverity
                                                }
                                            />
                                        )}
                                    />
                                </ToolbarItem>
                                {Object.keys(state.filterStates || {}).length >
                                    0 && (
                                    <ToolbarItem>
                                        <Button
                                            variant="link"
                                            onClick={handleClearFilters}
                                        >
                                            {t("filters.clear")}
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
    );
};

export default TasksTable;
