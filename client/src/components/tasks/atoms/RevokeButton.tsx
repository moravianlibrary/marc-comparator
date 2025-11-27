import { Button, Icon } from "@patternfly/react-core";
import { useRevokeTask } from "../../../hooks/useTasks";
import { TimesIcon } from "@patternfly/react-icons";

const RevokeTaskButton = ({ _id, status }: { _id: string; status: string }) => {
    const { mutate, isPending } = useRevokeTask();
    return (
        <Button
            variant="plain"
            isDanger
            size="sm"
            isDisabled={
                isPending || (status !== "Pending" && status !== "Started")
            }
            icon={
                <Icon
                    status={
                        status !== "Pending" && status !== "Started"
                            ? undefined
                            : "danger"
                    }
                    isInline
                >
                    <TimesIcon />
                </Icon>
            }
            onClick={() => mutate(_id)}
        />
    );
};

export default RevokeTaskButton;
