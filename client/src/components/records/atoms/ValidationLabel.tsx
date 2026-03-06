import { Badge, Label, LabelGroup } from "@patternfly/react-core";
import type { ReactElement } from "react";
import { useNavigate } from "react-router";
import { validityColor } from "../../../models/ui/validation";
import type { ValidityStatus } from "../../../models/primitives/validation";
import type { EsHit } from "../../../models/api/responses/es";
import type { CatalogRecord } from "../../../models/api/responses/catalog_record";
import type { Validation } from "../../../models/api/responses/validation";

const ValidationLabel = ({
    recordId,
    validator,
    status,
    occurences,
}: {
    recordId: string;
    validator: string;
    status: ValidityStatus;
    occurences: number;
}): ReactElement => {
    const navigate = useNavigate();

    return (
        <Label
            color={validityColor(status as ValidityStatus)}
            onClick={() =>
                navigate(
                    `/records/details?id=${recordId}&tab=validations&validations.validator=${validator}`,
                )
            }
        >
            {validator} {occurences > 1 && <Badge isRead>{occurences}</Badge>}
        </Label>
    );
};

type GroupedValidation = {
    validator: string;
    status: ValidityStatus;
    occurences: number;
};

const STATUS_ORDER: Record<ValidityStatus, number> = {
    Invalid: 0,
    ForReview: 1,
    AdditionalInfo: 2,
    Valid: 3,
};

const ValidationLabelGroup = ({
    hit: {
        _id,
        _source: { validations },
    },
    orderBy,
}: {
    hit: EsHit<CatalogRecord>;
    orderBy?: (validator: string) => number;
}) => {
    if (!validations || validations.length === 0) return null;

    const groupedValidations: GroupedValidation[] = Object.values(
        validations.reduce<Record<string, GroupedValidation>>(
            (acc, validation: Validation) => {
                const { validator, status } = validation;
                const key = `${validator}__${status}`;
                if (acc[key]) {
                    acc[key] = {
                        ...acc[key],
                        occurences: acc[key].occurences + 1,
                    };
                } else {
                    acc[key] = { validator, status, occurences: 1 };
                }
                return acc;
            },
            {},
        ),
    ).sort((a, b) => {
        if (orderBy) {
            const diffValidator = orderBy(a.validator) - orderBy(b.validator);
            if (diffValidator !== 0) return diffValidator;
        }

        const diffStatus = STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
        if (diffStatus !== 0) return diffStatus;

        return b.occurences - a.occurences;
    });

    return (
        <LabelGroup>
            {groupedValidations.map(({ validator, status, occurences }) => (
                <ValidationLabel
                    key={`${validator}__${status}`}
                    validator={validator}
                    status={status}
                    occurences={occurences}
                    recordId={_id}
                />
            ))}
        </LabelGroup>
    );
};

export { ValidationLabel, ValidationLabelGroup };
