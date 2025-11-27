import { Button, Icon } from "@patternfly/react-core";
import type { EsHit } from "../../../models/api/responses/es";
import type { Task } from "../../../models/api/responses/task";
import { DetailsIcon } from "../../atoms/Icons";
import { useNavigate } from "react-router";

const ShowTaskDetailsButton = ({ hit: { _id } }: { hit: EsHit<Task> }) => {
    const navigate = useNavigate();

    return (
        <Button
            variant="plain"
            isDanger
            size="sm"
            icon={
                <Icon isInline>
                    <DetailsIcon />
                </Icon>
            }
            onClick={() => navigate(`/tasks/details?id=${_id}`)}
        />
    );
};

export default ShowTaskDetailsButton;
