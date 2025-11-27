import { Label, LabelGroup } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useNavigate } from "react-router";
import type { Validation } from "../../../models/api/responses/validation";
import { validityColor } from "../../../models/ui/validation";
import type { ValidityStatus } from "../../../models/primitives/validation";
import type { EsHit } from "../../../models/api/responses/es";
import type { CatalogRecord } from "../../../models/api/responses/catalog_record";

const ValidationLabel = ({
    recordId,
    validation: { validator, status },
}: {
    recordId: string;
    validation: Validation;
}): ReactElement => {
    const navigate = useNavigate();

    return (
        <Label
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

const ValidationLabelGroup = ({
    hit: {
        _id,
        _source: { validations },
    },
}: {
    hit: EsHit<CatalogRecord>;
}) => {
    if (!validations || validations.length === 0) return null;

    return (
        <LabelGroup>
            {validations.map((validation, index) => (
                <ValidationLabel
                    key={index}
                    validation={validation}
                    recordId={_id}
                />
            ))}
        </LabelGroup>
    );
};

export { ValidationLabel, ValidationLabelGroup };
