import { useMemo, useRef, type ReactElement } from "react";
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
import { type CollectionData } from "../store/collection/domain";
import { buildRequests } from "../store/es/requests_factory";
import { buildCollectionData } from "../store/collection/data_factory";
import type { Task } from "../models/api/responses/task";
import { useSearchTasksBatch } from "../hooks/useTasks";
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
import { useTranslation } from "react-i18next";
import RevokeTaskButton from "../components/tasks/atoms/RevokeButton";
import ShowTaskDetailsButton from "../components/tasks/atoms/ShowDetailsButton";
import TaskName from "../components/tasks/atoms/TaskName";
import TaskTypeText from "../components/tasks/atoms/TaskTypeText";
import { useSearchParamsState } from "../hooks/useSearchParamsState";
import { EsStateSchema } from "../store/es/domain";
import { esStateReducer } from "../store/es/reducer";

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
const TASK_SEVERITY_ORDER: Record<string, number> =
    TaskSeveritySchema.options.reduce((acc, severity, index) => {
        acc[severity] = index;
        return acc;
    }, {} as Record<string, number>);

const TasksTable = (): ReactElement => {
    const { t } = useTranslation("tasks");

    const { state, dispatch } = useSearchParamsState(EsStateSchema, {
        storeKey: "tasksTable",
        reducer: esStateReducer,
        defaultValues: {
            config: {
                columnFields: {
                    run_time: ["started_at", "finished_at"],
                    details: [],
                    revoke: [],
                },
                filters: {
                    type: { type: "terms", size: 10 },
                    status: { type: "terms", size: 10 },
                    severity: { type: "terms", size: 4 },
                },
                sortBy: { default: [{ created_at: { order: "desc" } }] },
                perPage: { options: [10, 25, 50, 100], default: 10 },
            },
            columns: {
                name: { order: 0, visible: true },
                type: { order: 1, visible: true },
                status: { order: 2, visible: true },
                severity: { order: 3, visible: true },
                run_time: { order: 4, visible: true },
                details: { order: 5, visible: true },
                revoke: { order: 6, visible: true },
            },
            sortBy: "default",
        },
    });
    const { data: me } = useGetMe();

    const requests = useMemo(
        () => buildRequests(state),
        [state.page, state.perPage, JSON.stringify(state.terms), state.sortBy]
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

    const { isLoading, isError, error, hits, totalItems } = data;

    const handlePaginationChange = (newPage: number, newPerPage?: number) => {
        dispatch({
            type: "setPaginationParams",
            page: newPage,
            perPage: newPerPage || state.perPage || 0,
        });
    };

    const handleClearFilters = () => {
        dispatch({ type: "clearFilters" });
    };

    const countActiveFilters = Object.values(state.terms || {}).reduce(
        (acc, val) => acc + (val.include?.length || 0),
        0
    );

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
                                        data={data}
                                        state={state}
                                        dispatch={dispatch}
                                        bucketsOrdering={(a, b) =>
                                            TASK_TYPE_ORDER[a.key] -
                                            TASK_TYPE_ORDER[b.key]
                                        }
                                        placeholder={t(
                                            "filters.type-placeholder"
                                        )}
                                        renderBucketLabel={({ key }) => (
                                            <TaskTypeText
                                                type={key as TaskType}
                                            />
                                        )}
                                    />
                                </ToolbarItem>
                                <ToolbarItem>
                                    <TermFilterCheckboxMenu
                                        field="status"
                                        data={data}
                                        state={state}
                                        dispatch={dispatch}
                                        bucketsOrdering={(a, b) =>
                                            TASK_STATUS_ORDER[a.key] -
                                            TASK_STATUS_ORDER[b.key]
                                        }
                                        placeholder={t(
                                            "filters.status-placeholder"
                                        )}
                                        renderBucketLabel={({ key }) => (
                                            <TaskStatusLabel
                                                status={key as TaskStatus}
                                            />
                                        )}
                                    />
                                </ToolbarItem>
                                <ToolbarItem>
                                    <TermFilterCheckboxMenu
                                        field="severity"
                                        data={data}
                                        state={state}
                                        dispatch={dispatch}
                                        bucketsOrdering={(a, b) =>
                                            TASK_SEVERITY_ORDER[a.key] -
                                            TASK_SEVERITY_ORDER[b.key]
                                        }
                                        placeholder={t(
                                            "filters.severity-placeholder"
                                        )}
                                        renderBucketLabel={({ key }) => (
                                            <TaskSeverityLabel
                                                severity={key as TaskSeverity}
                                            />
                                        )}
                                    />
                                </ToolbarItem>
                                {countActiveFilters > 0 && (
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
                    state={state}
                    dispatch={dispatch}
                    isLoading={isLoading}
                    isError={isError}
                    error={error}
                    hits={hits}
                    getColumnLabel={(key) =>
                        t(`fields.${key.replaceAll("_", "-")}`)
                    }
                    renderCell={(key, hit) => {
                        switch (key) {
                            case "name":
                                return <TaskName hit={hit} />;
                            case "type":
                                return <TaskTypeText hit={hit} />;
                            case "status":
                                return (
                                    <TaskStatusLabel
                                        status={hit._source.status!}
                                    />
                                );
                            case "severity":
                                return (
                                    <TaskSeverityLabel
                                        severity={hit._source.severity!}
                                    />
                                );
                            case "run_time":
                                return hit._source.started_at ? (
                                    <RuntimeValue
                                        startedAt={hit._source.started_at}
                                        finishedAt={
                                            hit._source.finished_at ?? null
                                        }
                                    />
                                ) : null;
                            case "details":
                                return <ShowTaskDetailsButton hit={hit} />;
                            case "revoke":
                                return (
                                    <RevokeTaskButton
                                        _id={hit._id}
                                        status={hit._source.status!}
                                    />
                                );
                            default:
                                return null;
                        }
                    }}
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
                        perPageOptions={state.config.perPage.options.map(
                            (o) => ({
                                value: o,
                                title: o.toString(),
                            })
                        )}
                        itemCount={totalItems}
                        page={state.page}
                        perPage={state.perPage}
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
