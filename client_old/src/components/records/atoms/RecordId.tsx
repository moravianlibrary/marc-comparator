import { Button } from "@patternfly/react-core";
import MonospaceValue from "../../atoms/MonospaceValue";
import { ExternalLinkSquareAltIcon } from "@patternfly/react-icons";
import { useNavigate } from "react-router";

interface RecordIdProps {
    recordId: string;
    target?: "details" | "catalog";
}

const RecordId = ({ recordId, target = "details" }: RecordIdProps) => {
    const navigate = useNavigate();

    const ref =
        target === "details"
            ? `/records/details?id=${recordId}`
            : "/records/catalog?id=" + recordId;

    return (
        <Button
            variant="link"
            isInline
            hasNoPadding
            icon={<ExternalLinkSquareAltIcon />}
            iconPosition="end"
            onClick={() => navigate(ref)}
        >
            <MonospaceValue value={recordId} />
        </Button>
    );
};

export default RecordId;
