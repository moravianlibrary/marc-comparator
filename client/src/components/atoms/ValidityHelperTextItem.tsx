import { HelperTextItem } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { InfoIcon } from "@patternfly/react-icons";
import type { ValidityStatus } from "../../models/primitives/validation";

interface ValidityHelperTextItemProps {
    status: ValidityStatus;
    text: string;
}

const ValidityHelperTextItem = ({
    status,
    text,
}: ValidityHelperTextItemProps): ReactElement => {
    if (status === "Valid")
        return <HelperTextItem variant="success">{text}</HelperTextItem>;
    if (status === "Invalid")
        return <HelperTextItem variant="error">{text}</HelperTextItem>;
    if (status === "Warning")
        return <HelperTextItem variant="warning">{text}</HelperTextItem>;
    return (
        <HelperTextItem icon={<InfoIcon color="#0066CC" />}>
            {text}
        </HelperTextItem>
    );
};

export default ValidityHelperTextItem;
