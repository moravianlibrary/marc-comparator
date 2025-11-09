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
import { Fragment, ReactElement, useCallback, useMemo, useState } from "react";
import CheckboxSelect from "../components/molecules/CheckboxSelect";
import { TaskSeveritySchema, TaskTypeSchema } from "../models/primitives/task";
import { useRecreateIndexes } from "../hooks/useSystem";
import { useDeleteTasks } from "../hooks/useTasks";

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
                ? "Date must be at least one month old."
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
            title="Delete Old Tasks"
            description="Remove old tasks to free up database space and keep your system clean."
            action="Delete Old Tasks"
            onActionClick={handleDelete}
            isActionDisabled={!date}
        >
            <DescriptionList>
                <DescriptionListGroup>
                    <DescriptionListTermHelpText>
                        <Popover
                            headerContent="Delete tasks older than"
                            bodyContent="Tasks must be at least one month old to be deleted."
                        >
                            <DescriptionListTermHelpTextButton>
                                Delete tasks older than
                            </DescriptionListTermHelpTextButton>
                        </Popover>
                    </DescriptionListTermHelpText>
                    <DescriptionListDescription>
                        <DatePicker
                            value={date?.toISOString().slice(0, 10)}
                            placeholder="Select cutoff date"
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
                        Delete only tasks of type
                    </DescriptionListTerm>
                    <DescriptionListDescription>
                        <CheckboxSelect
                            placeholder="Select task types"
                            options={TaskTypeSchema.options.map((opt) => ({
                                label: opt,
                                value: opt,
                            }))}
                            selected={selectedTypes}
                            onChange={setSelectedTypes}
                        />
                    </DescriptionListDescription>
                </DescriptionListGroup>

                <DescriptionListGroup>
                    <DescriptionListTerm>
                        Delete only tasks with outcome severity
                    </DescriptionListTerm>
                    <DescriptionListDescription>
                        <CheckboxSelect
                            placeholder="Select outcome severities"
                            options={TaskSeveritySchema.options.map((opt) => ({
                                label: opt,
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
    const recreateIndexesMutation = useRecreateIndexes();

    return (
        <Fragment>
            <PageGroup stickyOnBreakpoint={{ default: "top" }}>
                <PageSection>
                    <Content>
                        <h1>System Maintenance</h1>
                        <p>
                            Perform periodic housekeeping tasks to ensure smooth
                            system performance and data integrity.
                        </p>
                    </Content>
                </PageSection>
            </PageGroup>

            <PageSection>
                <Gallery hasGutter minWidths={{ default: "400px" }}>
                    <MaintenanceCard
                        title="Recreate Indexes"
                        description="If you experience issues with searching or indexing, you can safely recreate the indexes."
                        action="Recreate Indexes"
                        onActionClick={() => recreateIndexesMutation.mutate()}
                    />

                    <DeleteOldTasksCard />
                </Gallery>
            </PageSection>
        </Fragment>
    );
};

export default SystemMaintenance;
