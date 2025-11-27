import { Table, Tbody } from "@patternfly/react-table";
import { type ReactElement } from "react";
import { useGetMarcRecord } from "../../hooks/useCatalogRecords";
import TableLoadingBody from "../molecules/TableLoadingBody";
import TableMessageBody from "../molecules/TableMessageBody";
import MarcFixedFieldRow from "../molecules/MarcFixedFieldRow";
import MarcVariableFieldRow from "../molecules/MarcVariableFieldRow";
import type { MarcRecord } from "../../models/api/responses/marc_record";

interface MarcRecordTableProps {
    base?: string;
    systemNumber?: string;
    record?: MarcRecord;
    isLoading?: boolean;
    noRecordMessage?: string;
    includeOnlyFields?: string[];
    renderFieldDetail?: (tag: string, fieldIdx: number) => React.ReactNode;
    renderSubfieldDetail?: (
        tag: string,
        fieldIdx: number,
        code: string,
        subfieldIdx: number,
        value: string
    ) => React.ReactNode;
    getHighlightedCodes?: (tag: string, fieldIdx: number) => string[];
}

const MarcRecordTable = ({
    base,
    record: recordInput,
    isLoading: isLoadingInput,
    systemNumber,
    noRecordMessage = "No record available",
    includeOnlyFields,
    renderFieldDetail,
    renderSubfieldDetail,
    getHighlightedCodes,
}: MarcRecordTableProps): ReactElement => {
    const { data, isLoading: isLoadingHook } = useGetMarcRecord(
        base || "",
        systemNumber || "",
        !!base && !!systemNumber
    );

    const record = recordInput || data;
    const isLoading = isLoadingInput || isLoadingHook;

    const renderFixedField = (tag: string, value: string) =>
        !includeOnlyFields || includeOnlyFields.includes(tag) ? (
            <MarcFixedFieldRow
                key={tag}
                term={tag}
                value={value}
                renderFieldDetail={renderFieldDetail}
            />
        ) : null;

    const renderVariableField = (
        tag: string,
        ind1: string,
        ind2: string,
        subfields: Record<string, string[]>,
        index: number
    ) =>
        !includeOnlyFields || includeOnlyFields.includes(tag) ? (
            <MarcVariableFieldRow
                key={`${tag}-${index}-variable-field`}
                tag={tag}
                ind1={ind1}
                ind2={ind2}
                subfields={subfields}
                index={index}
                highlightedCodes={
                    getHighlightedCodes
                        ? getHighlightedCodes(tag, index)
                        : undefined
                }
                renderFieldDetail={renderFieldDetail}
                renderSubfieldDetail={
                    renderSubfieldDetail
                        ? (code, idx, value) =>
                              renderSubfieldDetail(tag, index, code, idx, value)
                        : undefined
                }
            />
        ) : null;

    return (
        <Table variant="compact">
            {isLoading ? (
                <TableLoadingBody colSpan={3} />
            ) : !record ? (
                <TableMessageBody colSpan={3} message={noRecordMessage} />
            ) : (
                <Tbody isEvenStriped isExpanded>
                    <MarcFixedFieldRow
                        key="id"
                        term="System Number"
                        value={systemNumber || ""}
                    />
                    {includeOnlyFields &&
                    !includeOnlyFields.includes("leader") ? null : (
                        <MarcFixedFieldRow
                            key="leader"
                            term="Leader"
                            value={record.leader}
                        />
                    )}
                    {Object.entries(record.fixed_fields)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([tag, value]) => renderFixedField(tag, value))}
                    {Object.entries(record.variable_fields)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([tag, fields]) =>
                            fields.map(({ ind1, ind2, subfields }, subIndex) =>
                                renderVariableField(
                                    tag,
                                    ind1,
                                    ind2,
                                    subfields,
                                    subIndex
                                )
                            )
                        )}
                </Tbody>
            )}
        </Table>
    );
};

export default MarcRecordTable;
