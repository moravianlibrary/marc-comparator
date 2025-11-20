import { type ReactElement } from "react";
import {
    Bullseye,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    HelperText,
} from "@patternfly/react-core";
import type { Validation } from "../../models/api/responses/validation";
import ValidityHelperTextItem from "../atoms/ValidityHelperTextItem";
import MarcDetailRow from "../molecules/MarcDetailRow";
import MarcRecordTable from "./MarcRecordTable";

interface MarcValidationTableProps {
    base?: string;
    systemNumber?: string;
    noRecordMessage?: string;
    validations?: Validation[];
    showOnlyTarget?: boolean;
}

const MarcValidationTable = ({
    base,
    systemNumber,
    noRecordMessage = "No MARC record available",
    validations,
    showOnlyTarget,
}: MarcValidationTableProps): ReactElement => {
    if (!validations) {
        return <Bullseye>No validations provided</Bullseye>;
    }

    const validationsLookup = validations.reduce<
        Record<string, Record<number, Validation>>
    >((acc, validation) => {
        const tag = validation.target.tag;

        if (validation.target.idx === undefined) {
            acc[tag] = { 0: validation };
        } else {
            if (!acc[tag] || !(acc[tag] instanceof Object)) {
                acc[tag] = {};
            }

            (acc[tag] as Record<number, Validation>)[validation.target.idx] =
                validation;
        }

        return acc;
    }, {});

    const renderValidationDetail = (
        tag: string,
        index: number
    ): ReactElement | undefined => {
        if (!(tag in validationsLookup) || !(index in validationsLookup[tag])) {
            return undefined;
        }

        const validation = validationsLookup[tag][index];

        return (
            <MarcDetailRow
                key={`validation-${validation.target.tag}-${validation.target.idx}`}
                showMoreContent={
                    (validation.details || validation.hints) && (
                        <DescriptionList isHorizontal>
                            {validation.details && (
                                <DescriptionListGroup>
                                    <DescriptionListTerm>
                                        Details
                                    </DescriptionListTerm>
                                    <DescriptionListDescription>
                                        {validation.details}
                                    </DescriptionListDescription>
                                </DescriptionListGroup>
                            )}
                            {validation.hints && (
                                <DescriptionListGroup>
                                    <DescriptionListTerm>
                                        Hints
                                    </DescriptionListTerm>
                                    <DescriptionListDescription>
                                        {validation.hints}
                                    </DescriptionListDescription>
                                </DescriptionListGroup>
                            )}
                        </DescriptionList>
                    )
                }
            >
                <HelperText>
                    <ValidityHelperTextItem
                        status={validation.status}
                        text={validation.reason || "No reason provided"}
                    />
                </HelperText>
            </MarcDetailRow>
        );
    };

    return (
        <MarcRecordTable
            base={base}
            systemNumber={systemNumber}
            includeOnlyFields={
                showOnlyTarget
                    ? validations?.map((v) => v.target.tag)
                    : undefined
            }
            renderFieldDetail={renderValidationDetail}
            noRecordMessage={noRecordMessage}
        />
    );
};

export default MarcValidationTable;
