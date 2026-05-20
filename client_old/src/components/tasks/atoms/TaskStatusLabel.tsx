import { Label } from "@patternfly/react-core";
import type { ReactElement } from "react";
import type { TaskStatus } from "../../../models/primitives/task";
import { useTranslation } from "react-i18next";

interface TaskStatusLabelProps {
    status: TaskStatus;
}

const STATUS_COLOR_MAP: Record<
    TaskStatus,
    "grey" | "blue" | "green" | "red" | "orange"
> = {
    Pending: "grey",
    Started: "blue",
    Success: "green",
    Failure: "red",
    Revoked: "orange",
};

const TaskStatusLabel = ({ status }: TaskStatusLabelProps): ReactElement => {
    const { t } = useTranslation("tasks");

    return (
        <Label color={STATUS_COLOR_MAP[status]}>{t(`status.${status}`)}</Label>
    );
};

export default TaskStatusLabel;
