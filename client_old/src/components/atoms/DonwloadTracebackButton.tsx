import DownloadButton from "./DownloadButton";
import { DownloadIcon } from "@patternfly/react-icons";
import type { TaskStatus } from "../../models/primitives/task";
import { useDownloadTraceback } from "../../hooks/useTasks";

interface DownloadTracebackButtonProps {
    task_id: string;
    status: TaskStatus;
    traceback_lines: number | null;
}

const DownloadTracebackButton = ({
    task_id,
    status,
    traceback_lines,
}: DownloadTracebackButtonProps) => {
    const { download, isFetching } = useDownloadTraceback(task_id);

    return (
        <DownloadButton
            variant="plain"
            aria-label="Download traceback"
            isDisabled={status === "Pending" || !traceback_lines}
            icon={<DownloadIcon />}
            download={download}
            isLoading={isFetching}
        />
    );
};

export default DownloadTracebackButton;
