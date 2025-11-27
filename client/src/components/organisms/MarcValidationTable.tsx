import { type ReactElement } from "react";
import {
    Bullseye,
    Card,
    CardBody,
    CardHeader,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    HelperText,
    Spinner,
} from "@patternfly/react-core";
import type { Validation } from "../../models/api/responses/validation";
import ValidityHelperTextItem from "../atoms/ValidityHelperTextItem";
import MarcRecordTable from "./MarcRecordTable";
import { useTranslation } from "react-i18next";
import { useGetMarcRecord } from "../../hooks/useCatalogRecords";
import type {
    MarcRecord,
    VariableField,
} from "../../models/api/responses/marc_record";

interface MarcValidationTableProps {
    base?: string;
    systemNumber?: string;
    validations?: Validation[];
    showOnlyTarget?: boolean;
}

function addEmptyTargetIfMissing(
    record: MarcRecord,
    validations: Validation[]
): MarcRecord {
    if (!validations || validations.length === 0) return record;

    const tag = validations[0].target.tag;

    if (tag < "010") {
        if (tag in record.fixed_fields) return record;

        const newFixedFields: Record<string, string> = {};

        for (const fieldTag in record.fixed_fields) {
            if (fieldTag > tag) {
                newFixedFields[tag] = "-";
            }
            newFixedFields[fieldTag] = record.fixed_fields[fieldTag];
        }

        return {
            ...record,
            fixed_fields: newFixedFields,
        };
    }

    if (tag in record.variable_fields) return record;

    const newVariableFields: Record<string, VariableField[]> = {};

    for (const fieldTag in record.variable_fields) {
        if (fieldTag > tag) {
            newVariableFields[tag] = [{ ind1: "-", ind2: "-", subfields: {} }];
        }
        newVariableFields[fieldTag] = record.variable_fields[fieldTag];
    }

    return {
        ...record,
        variable_fields: newVariableFields,
    };
}

const MarcValidationTable = ({
    base,
    systemNumber,
    validations,
    showOnlyTarget,
}: MarcValidationTableProps): ReactElement => {
    const { t } = useTranslation();

    const { data: record, isLoading: isLoading } = useGetMarcRecord(
        base || "",
        systemNumber || "",
        !!base && !!systemNumber
    );

    if (!record || isLoading) {
        return (
            <Bullseye>
                <Spinner />
            </Bullseye>
        );
    }

    if (!validations) {
        return (
            <Bullseye>
                {t("records:details.validations.no-record-message")}
            </Bullseye>
        );
    }

    const validationsLookup = validations.reduce<
        Record<string, Record<number, Validation>>
    >((acc, validation) => {
        const tag = validation.target.tag;

        if (!validation.target.idx) {
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
            <Card isCompact isPlain>
                <CardHeader>
                    <HelperText>
                        <ValidityHelperTextItem
                            status={validation.status}
                            text={
                                t(
                                    `${validation.validator}:${validation.reason}`
                                ) || t("records:details.validations.no-reason")
                            }
                        />
                    </HelperText>
                </CardHeader>
                <CardBody>
                    {(validation.details || validation.hint) && (
                        <DescriptionList isHorizontal>
                            {validation.details && (
                                <DescriptionListGroup>
                                    <DescriptionListTerm>
                                        {t(
                                            "records:details.validations.details"
                                        )}
                                    </DescriptionListTerm>
                                    <DescriptionListDescription>
                                        {t(
                                            `${validation.validator}:${validation.details}`
                                        )}
                                    </DescriptionListDescription>
                                </DescriptionListGroup>
                            )}
                            {validation.hint && (
                                <DescriptionListGroup>
                                    <DescriptionListTerm>
                                        {t("records:details.validations.hint")}
                                    </DescriptionListTerm>
                                    <DescriptionListDescription>
                                        {t(
                                            `${validation.validator}:${validation.hint}`
                                        )}
                                    </DescriptionListDescription>
                                </DescriptionListGroup>
                            )}
                        </DescriptionList>
                    )}
                </CardBody>
            </Card>
        );
    };

    return (
        <MarcRecordTable
            record={addEmptyTargetIfMissing(record, validations)}
            systemNumber={systemNumber}
            includeOnlyFields={
                showOnlyTarget
                    ? validations?.map((v) => v.target.tag)
                    : undefined
            }
            renderFieldDetail={renderValidationDetail}
            noRecordMessage={t("records:details.validations.no-record-message")}
        />
    );
};

export default MarcValidationTable;
