import { Table, Tbody, Td, Tr } from "@patternfly/react-table";
import { type ReactElement } from "react";
import { useGetMarcRecord } from "../../hooks/useCatalogRecords";
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
    Stack,
    StackItem,
} from "@patternfly/react-core";
import MonospaceValue from "../atoms/MonospaceValue";
import type {
    Comparison,
    FieldComparisonResult,
    SubfieldComparisonResult,
} from "../../models/api/responses/comparison";
import MarcRecordTable from "./MarcRecordTable";
import MarcDetailRow from "../molecules/MarcDetailRow";
import type { MarcRecord } from "../../models/api/responses/marc_record";
import ValidityHelperTextItem from "../atoms/ValidityHelperTextItem";
import { scoreToValidity } from "../../models/ui/comparison";

interface MarcComparisonTableProps {
    base?: string;
    systemNumber?: string;
    comparison?: Comparison;
    noDataMessage?: string;
}

type FieldLookup = Record<
    string,
    Record<
        number,
        {
            result?: FieldComparisonResult;
            valueOther?: string;
            subfields?: Record<
                string,
                Record<
                    number,
                    { result: SubfieldComparisonResult; valueOther?: string }
                >
            >;
        }
    >
>;

function buildEnrichedRecord(recordA: MarcRecord, comparison: Comparison) {
    const enrichedRecord: MarcRecord = {
        leader: recordA.leader,
        fixed_fields: structuredClone(recordA.fixed_fields),
        variable_fields: structuredClone(recordA.variable_fields),
    };

    for (const field of comparison.field_results || []) {
        const tag = field.tag;

        if (tag < "010") {
            if (!(tag in enrichedRecord.fixed_fields)) {
                enrichedRecord.fixed_fields[tag] = "-";
            }
            continue;
        }

        if (!(tag in enrichedRecord.variable_fields)) {
            enrichedRecord.variable_fields[tag] = [
                {
                    ind1: " ",
                    ind2: " ",
                    subfields: field.subfield_results
                        ? field.subfield_results.reduce<
                              Record<string, string[]>
                          >((acc, sr) => {
                              acc[sr.code] = ["-"];
                              return acc;
                          }, {})
                        : { "-": ["-"] },
                },
            ];
            continue;
        }

        if (enrichedRecord.variable_fields[tag].length <= (field.idxA ?? 0)) {
            enrichedRecord.variable_fields[tag].push({
                ind1: " ",
                ind2: " ",
                subfields: field.subfield_results
                    ? field.subfield_results.reduce<Record<string, string[]>>(
                          (acc, sr) => {
                              acc[sr.code] = ["-"];
                              return acc;
                          },
                          {}
                      )
                    : { "-": ["-"] },
            });
            continue;
        }

        if (enrichedRecord.variable_fields[tag][field.idxA ?? 0]) {
            for (const sub of field.subfield_results || []) {
                const code = sub.code;
                if (
                    !enrichedRecord.variable_fields[tag][field.idxA ?? 0]
                        .subfields[code]
                ) {
                    enrichedRecord.variable_fields[tag][
                        field.idxA ?? 0
                    ].subfields[code] = ["-"];
                } else if (
                    enrichedRecord.variable_fields[tag][field.idxA ?? 0]
                        .subfields[code].length <= (sub.idxA ?? 0)
                ) {
                    enrichedRecord.variable_fields[tag][
                        field.idxA ?? 0
                    ].subfields[code].push("-");
                }
            }
        }
    }

    return enrichedRecord;
}

function buildFieldLookup(
    otherRecord: MarcRecord,
    comparison: Comparison
): FieldLookup {
    const lookup: FieldLookup = {};

    for (const field of comparison.field_results || []) {
        const tag = field.tag;
        const fieldIdx = field.idxA ?? 0;

        if (!lookup[tag]) lookup[tag] = {};
        if (!lookup[tag][fieldIdx]) lookup[tag][fieldIdx] = { subfields: {} };

        const entry = lookup[tag][fieldIdx];

        // --- Field-level ---
        entry.result = field;

        // valueOther for fixed or variable field
        if (tag < "010") {
            entry.valueOther = otherRecord.fixed_fields[tag] ?? "-";
        }

        // --- Subfields ---
        for (const sub of field.subfield_results || []) {
            const code = sub.code;
            const subIdx = sub.idxA ?? 0;

            if (!entry.subfields![code]) entry.subfields![code] = {};

            // value from other record
            let valueOther: string | undefined = undefined;
            if (tag >= "010") {
                const bField =
                    otherRecord.variable_fields[tag]?.[field.idxB ?? 0];
                valueOther = bField?.subfields[code]?.[sub.idxB ?? 0] ?? "-";
            }

            entry.subfields![code][subIdx] = { result: sub, valueOther };
        }
    }

    return lookup;
}

const MarcComparisonTable = ({
    base: baseA,
    systemNumber: systemNumberA,
    comparison,
    noDataMessage = "No data available",
}: MarcComparisonTableProps): ReactElement => {
    const { data: recordA, isLoading: isLoadingA } = useGetMarcRecord(
        baseA || "",
        systemNumberA || "",
        !!baseA && !!systemNumberA
    );

    const baseB = comparison?.comparator;
    const systemNumberB = comparison?.system_number;
    const { data: recordB, isLoading: isLoadingB } = useGetMarcRecord(
        baseB || "",
        systemNumberB || "",
        !!baseB && !!systemNumberB
    );

    if (!comparison) {
        return <Bullseye>No comparison provided</Bullseye>;
    }

    const enrichedRecordA = recordA
        ? buildEnrichedRecord(recordA, comparison)
        : undefined;
    const fieldLookupMap = recordB
        ? buildFieldLookup(recordB, comparison)
        : undefined;

    const renderFieldDetail = (tag: string, index: number) => {
        const fieldLookup = fieldLookupMap?.[tag]?.[index];

        if (!fieldLookup || !fieldLookup.result) return null;

        // TODO: Details as info popover
        return (
            <MarcDetailRow key={`comparison-${tag}-${index}`}>
                <Stack>
                    <StackItem>
                        <HelperText>
                            <ValidityHelperTextItem
                                status={scoreToValidity(
                                    fieldLookup.result.score
                                )}
                                text={`${(
                                    fieldLookup.result.score * 100
                                ).toFixed(1)}% : 
                            ${
                                fieldLookup.result.explanation ||
                                "No explanation provided"
                            }`}
                            />
                        </HelperText>
                    </StackItem>
                    {fieldLookup.valueOther && (
                        <StackItem>{fieldLookup.valueOther}</StackItem>
                    )}
                </Stack>
            </MarcDetailRow>
        );
    };

    const renderSubfieldDetail = (
        tag: string,
        fieldIdx: number,
        code: string,
        subfieldIdx: number,
        value: string
    ): ReactElement | null => {
        const fieldLookup = fieldLookupMap?.[tag]?.[fieldIdx];
        const subfieldLookup = fieldLookup?.subfields?.[code]?.[subfieldIdx];

        if (!subfieldLookup) return null;

        return (
            <Card isCompact>
                <CardHeader>
                    <HelperText>
                        <ValidityHelperTextItem
                            status={scoreToValidity(
                                subfieldLookup.result.score
                            )}
                            text={`${(
                                subfieldLookup.result.score * 100
                            ).toFixed(1)}% : 
                            ${
                                subfieldLookup.result.explanation ||
                                "No explanation provided"
                            }`}
                        />
                    </HelperText>
                </CardHeader>
                <CardBody>{subfieldLookup.valueOther || "-"}</CardBody>
            </Card>
        );
    };

    return (
        <MarcRecordTable
            systemNumber={systemNumberA}
            record={enrichedRecordA}
            isLoading={isLoadingA || isLoadingB}
            renderFieldDetail={renderFieldDetail}
            renderSubfieldDetail={renderSubfieldDetail}
            // includeOnlyFields={
            //     showOnlyTarget
            //         ? validations?.map((v) => v.target.tag)
            //         : undefined
            // }
            noRecordMessage={noDataMessage}
        />
    );
};

export default MarcComparisonTable;
