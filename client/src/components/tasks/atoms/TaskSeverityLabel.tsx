import { Label } from "@patternfly/react-core";
import type { ReactElement } from "react";
import type { TaskSeverity } from "../../../models/primitives/task";
import { useTranslation } from "react-i18next";

interface TaskSeverityLabelProps {
    severity: TaskSeverity;
}

const SEVERITY_STATUS_MAP: Record<
    TaskSeverity,
    "success" | "warning" | "danger"
> = {
    Info: "success",
    Warning: "warning",
    Error: "danger",
    Critical: "danger",
};

const TaskSeverityLabel = ({
    severity,
}: TaskSeverityLabelProps): ReactElement => {
    const { t } = useTranslation("tasks");

    return (
        <Label status={SEVERITY_STATUS_MAP[severity]}>
            {t(`severity.${severity}`)}
        </Label>
    );
};

export default TaskSeverityLabel;
