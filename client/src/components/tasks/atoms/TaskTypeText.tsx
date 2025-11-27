import type { EsHit } from "../../../models/api/responses/es";
import type { Task } from "../../../models/api/responses/task";
import { useTranslation } from "react-i18next";
import type { TaskType } from "../../../models/primitives/task";

const TaskTypeText = ({
    hit,
    type,
}: {
    hit?: EsHit<Task>;
    type?: TaskType;
}) => {
    const { t } = useTranslation("tasks");

    const hitType = hit?._source?.type;

    if (!hitType && !type) {
        throw new Error("Either hit or type must be provided");
    }

    return <p>{t(`type.${type ?? hitType}`)}</p>;
};

export default TaskTypeText;
