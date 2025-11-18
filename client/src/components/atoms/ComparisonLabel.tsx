import { Label } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useNavigate } from "react-router";
import { scoreColor } from "../../models/ui/comparison";
import type { Comparison } from "../../models/api/responses/comparison";

interface ComparisonLabelProps {
    recordId: string;
    comparison: Comparison;
    key?: number | string;
}

const ComparisonLabel = ({
    recordId,
    comparison: { base, comparator, overall_score },
    key,
}: ComparisonLabelProps): ReactElement => {
    const navigate = useNavigate();

    return (
        <Label
            key={key}
            color={scoreColor(overall_score)}
            onClick={() =>
                navigate(
                    `/records/details?id=${recordId}&tab=comparisons&comparisons.comparator=${comparator}&comparisons.base=${base}`
                )
            }
        >
            {`${base} ${comparator}: ${overall_score}`}
        </Label>
    );
};

export default ComparisonLabel;
