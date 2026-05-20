import { HelperTextItem } from "@patternfly/react-core";
import type { ReactElement } from "react";
import type { MatchQuality } from "../../models/primitives/comparison";

interface ComparisonHelperTextItemProps {
    matchQuality: MatchQuality;
    text: string;
}

const ComparisonHelperTextItem = ({
    matchQuality,
    text,
}: ComparisonHelperTextItemProps): ReactElement => {
    if (matchQuality === "Excellent")
        return <HelperTextItem variant="success">{text}</HelperTextItem>;
    if (matchQuality === "Moderate")
        return <HelperTextItem variant="warning">{text}</HelperTextItem>;
    return <HelperTextItem variant="error">{text}</HelperTextItem>;
};

export default ComparisonHelperTextItem;
