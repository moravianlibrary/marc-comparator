import {
    Button,
    CodeBlock,
    CodeBlockAction,
    Content,
    Grid,
    GridItem,
    PageGroup,
    PageSection,
    Split,
    SplitItem,
} from "@patternfly/react-core";
import { Fragment, type ReactElement } from "react";
import { useSearchParamsState } from "../hooks/useSearchParamsState";
import z from "zod";
import { useGetTask, useGetTraceback } from "../hooks/useTasks";
import MonospaceValue from "../components/atoms/MonospaceValue";
import DownloadTracebackButton from "../components/atoms/DonwloadTracebackButton";
import type { EsHitTask } from "../models/api/responses/task";
import { AngleLeftIcon, AngleRightIcon } from "@patternfly/react-icons";
import { useTranslation } from "react-i18next";
import SimpleDescriptionList from "../components/molecules/SimpleDescriptionList";
import LoadingState from "../components/atoms/LoadingState";
import TaskName from "../components/tasks/atoms/TaskName";
import TaskType from "../components/tasks/atoms/TaskTypeText";
import TaskStatusLabel from "../components/tasks/atoms/TaskStatusLabel";
import TaskSeverityLabel from "../components/tasks/atoms/TaskSeverityLabel";
import { RedoIcon } from "@patternfly/react-icons";
import { useQueryClient } from "@tanstack/react-query";
import RuntimeValue from "../components/atoms/RuntimeValue";

const TaskTracebackState = z.object({
    from: z.number().min(0).default(0),
    size: z.number().min(1).max(1000).default(100),
});
const TaskDetailsState = z.object({
    id: z.string().nullable().default(null),
    traceback: TaskTracebackState.default(() => TaskTracebackState.parse({})),
});

const TasksDetailsPage = (): ReactElement => {
    const { t } = useTranslation("tasks");

    const [params, setParams] = useSearchParamsState(
        TaskDetailsState,
        "task-details-state"
    );

    const { data, isLoading } = useGetTask(params.id || "", Boolean(params.id));
    const queryClient = useQueryClient();

    const handleRefresh = () => {
        queryClient.invalidateQueries({
            queryKey: ["tasks", "get", params.id],
            exact: true,
        });
        queryClient.invalidateQueries({
            queryKey: ["tasks", "traceback", params.id],
            exact: false,
        });
    };

    if (!params.id) {
        return (
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>{t("details.title")}</h1>
                        <p>{t("details.select-task-instructions")}</p>
                    </Content>
                </PageSection>
            </PageGroup>
        );
    }

    if (isLoading) {
        return (
            <PageGroup>
                <PageSection>{t("details.loading")}</PageSection>
            </PageGroup>
        );
    }

    if (!data) {
        return (
            <PageGroup>
                <PageSection>{t("details.not-found")}</PageSection>
            </PageGroup>
        );
    }

    const handleGoToPreviousPage = () => {
        setParams({
            id: params.id,
            traceback: {
                from: Math.max(
                    0,
                    params.traceback.from - params.traceback.size
                ),
                size: params.traceback.size,
            },
        });
    };

    const handleGoToNextPage = () => {
        const { from, size } = params.traceback;
        const total = data._source.traceback_lines ?? 0;

        const nextFrom = total > from + size ? from + size : from;

        setParams({
            ...params,
            traceback: {
                ...params.traceback,
                from: nextFrom,
            },
        });
    };

    return (
        <>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <Split>
                            <SplitItem isFilled>
                                <h1>{t("details.title")}</h1>
                            </SplitItem>
                            <SplitItem>
                                <Button
                                    variant="plain"
                                    icon={<RedoIcon />}
                                    onClick={handleRefresh}
                                />
                            </SplitItem>
                        </Split>
                        <p>
                            {t("details.task-id")}
                            {": "}
                            <MonospaceValue value={params.id} />
                        </p>
                    </Content>
                </PageSection>
            </PageGroup>
            <PageGroup>
                <PageSection>
                    <SimpleDescriptionList
                        groups={[
                            {
                                term: t("fields.name"),
                                description: <TaskName hit={data} />,
                            },
                            {
                                term: t("fields.type"),
                                description: <TaskType hit={data} />,
                            },
                            {
                                term: t("fields.status"),
                                description: (
                                    <TaskStatusLabel
                                        status={data._source.status}
                                    />
                                ),
                            },
                            {
                                term: t("fields.severity"),
                                description: (
                                    <TaskSeverityLabel
                                        severity={data._source.outcome_severity}
                                    />
                                ),
                            },
                            {
                                term: t("fields.run-time"),
                                description: data._source.started_at ? (
                                    <RuntimeValue
                                        startedAt={data._source.started_at}
                                        finishedAt={
                                            data._source.finished_at ?? null
                                        }
                                    />
                                ) : (
                                    "-"
                                ),
                            },
                            {
                                term: t("fields.traceback"),
                                description:
                                    (data._source.traceback_lines || 0) > 0 ? (
                                        <TaskTraceback
                                            id={params.id}
                                            traceback={params.traceback}
                                            taskHit={data}
                                            onGoToPreviousPage={
                                                handleGoToPreviousPage
                                            }
                                            onGoToNextPage={handleGoToNextPage}
                                        />
                                    ) : (
                                        t("details.no-traceback")
                                    ),
                            },
                        ]}
                    />
                </PageSection>
            </PageGroup>
        </>
    );
};

const TaskTraceback = ({
    id,
    traceback,
    taskHit,
    onGoToPreviousPage,
    onGoToNextPage,
}: {
    id: string;
    traceback: z.infer<typeof TaskTracebackState>;
    taskHit: EsHitTask;
    onGoToPreviousPage: () => void;
    onGoToNextPage: () => void;
}): ReactElement => {
    const { data, isLoading } = useGetTraceback(id, {
        from: traceback.from,
        to: traceback.from + traceback.size,
    });

    if (isLoading || !data) {
        return <LoadingState />;
    }
    const lines = data.split("\n");

    return (
        <CodeBlock
            actions={
                <>
                    <CodeBlockAction>
                        <Button
                            variant="plain"
                            aria-label="traceback-page-right"
                            icon={<AngleLeftIcon />}
                            isDisabled={traceback.from === 0}
                            onClick={onGoToPreviousPage}
                        />
                    </CodeBlockAction>
                    <CodeBlockAction>
                        <Button
                            variant="plain"
                            aria-label="traceback-page-left"
                            icon={<AngleRightIcon />}
                            isDisabled={
                                !!taskHit._source.traceback_lines &&
                                traceback.from + traceback.size >=
                                    taskHit._source.traceback_lines
                            }
                            onClick={onGoToNextPage}
                        />
                    </CodeBlockAction>
                    <CodeBlockAction>
                        <DownloadTracebackButton
                            task_id={id}
                            status={taskHit._source.status}
                            traceback_lines={taskHit._source.traceback_lines}
                        />
                    </CodeBlockAction>
                </>
            }
        >
            <Grid>
                {lines.map((line, index) => (
                    <Fragment key={index}>
                        <GridItem span={1} style={{ textAlign: "right" }}>
                            <MonospaceValue value={`${index + 1}: `} />
                        </GridItem>
                        <GridItem span={11}>
                            <MonospaceValue value={line} />
                        </GridItem>
                    </Fragment>
                ))}
            </Grid>
        </CodeBlock>
    );
};

export default TasksDetailsPage;
