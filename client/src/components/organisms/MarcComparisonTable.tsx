import { type ReactElement } from "react";
import { useGetMarcRecord } from "../../hooks/useCatalogRecords";
import {
    Bullseye,
    Card,
    CardBody,
    CardHeader,
    Divider,
    HelperText,
    Stack,
    StackItem,
} from "@patternfly/react-core";
import type {
    Comparison,
    FieldComparisonResult,
    SubfieldComparisonResult,
} from "../../models/api/responses/comparison";
import MarcRecordTable from "./MarcRecordTable";
import type { MarcRecord } from "../../models/api/responses/marc_record";
import { useTranslation } from "react-i18next";
import MonospaceValue from "../atoms/MonospaceValue";
import SemiCircularGauge from "../atoms/SemiCircularGauge";
import ComparisonHelperTextItem from "../atoms/ComparisonHelperTextItem";
import { scoreToMatchQuality } from "../../models/ui/comparison";

interface MarcComparisonTableProps {
    base?: string;
    systemNumber?: string;
    comparison?: Comparison;
    showOnlyTarget?: boolean;
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
    showOnlyTarget,
}: MarcComparisonTableProps): ReactElement => {
    const { t } = useTranslation();

    const { data: recordA, isLoading: isLoadingA } = useGetMarcRecord(
        baseA || "",
        systemNumberA || "",
        !!baseA && !!systemNumberA
    );

    const baseB = comparison?.base;
    const systemNumberB = comparison?.system_number;
    const { data: recordB, isLoading: isLoadingB } = useGetMarcRecord(
        baseB || "",
        systemNumberB || "",
        !!baseB && !!systemNumberB
    );

    if (!comparison) {
        return (
            <Bullseye>
                {t("records:details.comparisons.no-comparison-selected")}
            </Bullseye>
        );
    }

    const enrichedRecordA = recordA
        ? buildEnrichedRecord(recordA, comparison)
        : undefined;
    const fieldLookupMap = recordB
        ? buildFieldLookup(recordB, comparison)
        : undefined;

    const scoreExplanationText = (
        score: number,
        explanation?: string | null
    ) => {
        const scoreStr = `${(score * 100).toFixed(1)}%`;

        if (!explanation) return scoreStr;

        return `${scoreStr}: ${t(`${comparison.comparator}:${explanation}`)}`;
    };

    const renderFieldDetail = (tag: string, index: number) => {
        const fieldLookup = fieldLookupMap?.[tag]?.[index];

        if (!fieldLookup || !fieldLookup.result) return null;

        // TODO: Details as info popover
        return (
            <Card isCompact isPlain>
                <CardHeader>
                    <HelperText>
                        <ComparisonHelperTextItem
                            matchQuality={scoreToMatchQuality(
                                fieldLookup.result.score
                            )}
                            text={scoreExplanationText(
                                fieldLookup.result.score,
                                fieldLookup.result.explanation
                            )}
                        />
                    </HelperText>
                </CardHeader>
                {fieldLookup.valueOther && (
                    <CardBody>
                        {tag < "010" ? (
                            <MonospaceValue value={fieldLookup.valueOther} />
                        ) : (
                            fieldLookup.valueOther
                        )}
                    </CardBody>
                )}
            </Card>
        );
    };

    const renderSubfieldDetail = (
        tag: string,
        fieldIdx: number,
        code: string,
        subfieldIdx: number,
        _: string
    ): ReactElement | null => {
        const fieldLookup = fieldLookupMap?.[tag]?.[fieldIdx];
        const subfieldLookup = fieldLookup?.subfields?.[code]?.[subfieldIdx];

        if (!subfieldLookup) return null;

        return (
            <Card isCompact>
                <CardHeader>
                    <HelperText>
                        <ComparisonHelperTextItem
                            matchQuality={scoreToMatchQuality(
                                subfieldLookup.result.score
                            )}
                            text={scoreExplanationText(
                                subfieldLookup.result.score,
                                subfieldLookup.result.explanation
                            )}
                        />
                    </HelperText>
                </CardHeader>
                <CardBody>{subfieldLookup.valueOther || "-"}</CardBody>
            </Card>
        );
    };

    return (
        <Stack hasGutter>
            <StackItem>
                <Bullseye>
                    <SemiCircularGauge value={comparison.overall_score * 100} />
                </Bullseye>
            </StackItem>
            <Divider />
            <StackItem>
                <MarcRecordTable
                    systemNumber={systemNumberA}
                    record={enrichedRecordA}
                    isLoading={isLoadingA || isLoadingB}
                    renderFieldDetail={renderFieldDetail}
                    renderSubfieldDetail={renderSubfieldDetail}
                    includeOnlyFields={
                        showOnlyTarget
                            ? comparison.field_results?.map((v) => v.tag)
                            : undefined
                    }
                    noRecordMessage={t("records:details.comparisons.no-record")}
                />
            </StackItem>
        </Stack>
    );
};

export default MarcComparisonTable;
