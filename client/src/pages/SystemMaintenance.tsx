import {
    Button,
    Card,
    CardBody,
    CardFooter,
    CardTitle,
    Content,
    DatePicker,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    DescriptionListTermHelpText,
    DescriptionListTermHelpTextButton,
    Gallery,
    PageGroup,
    PageSection,
    Popover,
} from "@patternfly/react-core";
import {
    Fragment,
    type ReactElement,
    useCallback,
    useMemo,
    useState,
} from "react";
import CheckboxSelect from "../components/molecules/CheckboxSelect";
import { TaskSeveritySchema, TaskTypeSchema } from "../models/primitives/task";
import { useRecreateIndexes } from "../hooks/useSystem";
import { useDeleteTasks } from "../hooks/useTasks";
import { useTranslation } from "react-i18next";

// -----------------------------------------------------------------------------
// Utility Components
// -----------------------------------------------------------------------------

/** Generic maintenance card layout */
const MaintenanceCard = ({
    title,
    description,
    action,
    onActionClick,
    isActionDisabled,
    children,
}: {
    title: string;
    description?: string;
    action: string;
    onActionClick: () => void;
    isActionDisabled?: boolean;
    children?: React.ReactNode;
}) => (
    <Card>
        <CardTitle>{title}</CardTitle>
        {description && (
            <CardBody>
                <Content>
                    <p>{description}</p>
                </Content>
            </CardBody>
        )}
        <CardBody>{children}</CardBody>
        <CardFooter>
            <Button
                variant="primary"
                onClick={onActionClick}
                isDisabled={isActionDisabled}
            >
                {action}
            </Button>
        </CardFooter>
    </Card>
);

// -----------------------------------------------------------------------------
// Delete Old Tasks Card
// -----------------------------------------------------------------------------

const DeleteOldTasksCard = (): ReactElement => {
    const { t } = useTranslation("system-maintenance");
    const { t: t_tasks } = useTranslation("tasks");

    const deleteTasksMutation = useDeleteTasks();

    const [date, setDate] = useState<Date>(() => {
        const d = new Date();
        d.setDate(d.getDate() - 90);
        return d;
    });
    const [selectedTypes, setSelectedTypes] = useState<
        { label: string; value: string }[]
    >([]);
    const [selectedSeverities, setSelectedSeverities] = useState<
        { label: string; value: string }[]
    >([]);

    const oneMonthAgo = useMemo(() => {
        const today = new Date();
        return new Date(
            today.getFullYear(),
            today.getMonth() - 1,
            today.getDate()
        );
    }, []);

    const validateDate = useCallback(
        (selectedDate: Date) =>
            selectedDate > oneMonthAgo
                ? t("validation.date-at-least-one-month-old")
                : "",
        [oneMonthAgo]
    );

    const handleDelete = () => {
        if (!date) return;

        const terms: any[] = [];

        if (selectedTypes.length > 0) {
            terms.push({
                terms: {
                    type: selectedTypes.map((t) => t.value),
                },
            });
        }
        if (selectedSeverities.length > 0) {
            terms.push({
                terms: {
                    outcome_severity: selectedSeverities.map((s) => s.value),
                },
            });
        }

        deleteTasksMutation.mutate({
            query: {
                bool: {
                    must: [
                        { range: { created_at: { lt: date.toISOString() } } },
                        ...terms,
                    ],
                },
            },
        });
    };

    return (
        <MaintenanceCard
            title={t("delete-old-tasks.title")}
            description={t("delete-old-tasks.description")}
            action={t("delete-old-tasks.action")}
            onActionClick={handleDelete}
            isActionDisabled={!date}
        >
            <DescriptionList>
                <DescriptionListGroup>
                    <DescriptionListTermHelpText>
                        <Popover
                            headerContent={t(
                                "delete-old-tasks.cutoff-date-title"
                            )}
                            bodyContent={t(
                                "delete-old-tasks.cutoff-date-description"
                            )}
                        >
                            <DescriptionListTermHelpTextButton>
                                {t("delete-old-tasks.cutoff-date-title")}
                            </DescriptionListTermHelpTextButton>
                        </Popover>
                    </DescriptionListTermHelpText>
                    <DescriptionListDescription>
                        <DatePicker
                            value={date?.toISOString().slice(0, 10)}
                            placeholder={t(
                                "delete-old-tasks.cutoff-date-placeholder"
                            )}
                            appendTo={() => document.body}
                            validators={[validateDate]}
                            onChange={(_, __, newDate) =>
                                newDate && setDate(newDate)
                            }
                        />
                    </DescriptionListDescription>
                </DescriptionListGroup>

                <DescriptionListGroup>
                    <DescriptionListTerm>
                        {t("delete-old-tasks.task-types-title")}
                    </DescriptionListTerm>
                    <DescriptionListDescription>
                        <CheckboxSelect
                            placeholder={t(
                                "delete-old-tasks.task-types-placeholder"
                            )}
                            options={TaskTypeSchema.options.map((opt) => ({
                                label: t_tasks(`type.${opt}`),
                                value: opt,
                            }))}
                            selected={selectedTypes}
                            onChange={setSelectedTypes}
                        />
                    </DescriptionListDescription>
                </DescriptionListGroup>

                <DescriptionListGroup>
                    <DescriptionListTerm>
                        {t("delete-old-tasks.task-severities-title")}
                    </DescriptionListTerm>
                    <DescriptionListDescription>
                        <CheckboxSelect
                            placeholder={t(
                                "delete-old-tasks.task-severities-placeholder"
                            )}
                            options={TaskSeveritySchema.options.map((opt) => ({
                                label: t_tasks(`severity.${opt}`),
                                value: opt,
                            }))}
                            selected={selectedSeverities}
                            onChange={setSelectedSeverities}
                        />
                    </DescriptionListDescription>
                </DescriptionListGroup>
            </DescriptionList>
        </MaintenanceCard>
    );
};

// -----------------------------------------------------------------------------
// Main View
// -----------------------------------------------------------------------------

const SystemMaintenance = (): ReactElement => {
    const { t } = useTranslation("system-maintenance");

    const recreateIndexesMutation = useRecreateIndexes();

    return (
        <Fragment>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>{t("title")}</h1>
                        <p>{t("description")}</p>
                    </Content>
                </PageSection>
            </PageGroup>

            <PageSection>
                <Gallery hasGutter minWidths={{ default: "400px" }}>
                    <MaintenanceCard
                        title={t("recreate-indexes.title")}
                        description={t("recreate-indexes.description")}
                        action={t("recreate-indexes.action")}
                        onActionClick={() => recreateIndexesMutation.mutate()}
                    />
                    <DeleteOldTasksCard />
                </Gallery>
            </PageSection>
        </Fragment>
    );
};

export default SystemMaintenance;
