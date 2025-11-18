import { Label } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useNavigate } from "react-router";
import type { Validation } from "../../models/api/responses/validation";
import { validityColor } from "../../models/ui/validation";
import type { ValidityStatus } from "../../models/primitives/validation";

interface ValidationLabelProps {
    recordId: string;
    validation: Validation;
    key?: number | string;
}

const ValidationLabel = ({
    recordId,
    validation: { validator, status },
    key,
}: ValidationLabelProps): ReactElement => {
    const navigate = useNavigate();

    return (
        <Label
            key={key}
            color={validityColor(status as ValidityStatus)}
            onClick={() =>
                navigate(
                    `/records/details?id=${recordId}&tab=validations&validations.validator=${validator}`
                )
            }
        >
            {validator}
        </Label>
    );
};

export default ValidationLabel;
