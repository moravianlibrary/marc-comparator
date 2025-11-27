import type { EsHit } from "../../../models/api/responses/es";
import type { Task } from "../../../models/api/responses/task";
// import { useTranslation } from "react-i18next";

const TaskName = ({
    hit: {
        _source: { name },
    },
}: {
    hit: EsHit<Task>;
}) => {
    // const { t } = useTranslation("tasks");
    // return <p>{t(`names.${name}`)}</p>;
    return <p>{name}</p>;
};

export default TaskName;
