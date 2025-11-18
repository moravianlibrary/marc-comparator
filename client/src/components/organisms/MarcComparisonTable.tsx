import { Table, Tbody, Td, Tr } from "@patternfly/react-table";
import { type ReactElement } from "react";
import { useGetMarcRecord } from "../../hooks/useCatalogRecords";
import {
    Bullseye,
    EmptyState,
    Spinner,
    Stack,
    StackItem,
} from "@patternfly/react-core";
import MonospaceValue from "../atoms/MonospaceValue";
import type { Comparison } from "../../models/api/responses/comparison";

interface MarcComparisonTableProps {
    comparison: Comparison;
    baseA?: string;
    systemNumberA?: string;
    baseB?: string;
    systemNumberB?: string;
    noDataMessage?: string;
}

const MarcComparisonTable = ({
    baseA,
    systemNumberA,
    baseB,
    systemNumberB,
    noDataMessage = "No data available",
}: MarcComparisonTableProps): ReactElement => {
    const { data: dataA, isLoading: isLoadingA } = useGetMarcRecord(
        baseA || "",
        systemNumberA || "",
        !!baseA && !!systemNumberA
    );
    const { data: dataB, isLoading: isLoadingB } = useGetMarcRecord(
        baseB || "",
        systemNumberB || "",
        !!baseB && !!systemNumberB
    );

    return (
        <Table variant="compact">
            {isLoadingA || isLoadingB ? (
                <Tbody>
                    <Tr>
                        <Td colSpan={4}>
                            <Bullseye>
                                <Spinner size="xl" />
                            </Bullseye>
                        </Td>
                    </Tr>
                </Tbody>
            ) : !dataA || !dataB ? (
                <Tbody>
                    <Tr>
                        <Td colSpan={4}>
                            <Bullseye>
                                <EmptyState>{noDataMessage}</EmptyState>
                            </Bullseye>
                        </Td>
                    </Tr>
                </Tbody>
            ) : (
                <Tbody isEvenStriped>
                    <Tr key="idA">
                        <Td>
                            <MonospaceValue value={`${baseA} System Number`} />
                        </Td>
                        <Td></Td>
                        <Td></Td>
                        <Td>
                            <MonospaceValue value={systemNumberA || ""} />
                        </Td>
                    </Tr>
                    <Tr key="idB">
                        <Td>
                            <MonospaceValue value={`${baseB} System Number`} />
                        </Td>
                        <Td></Td>
                        <Td></Td>
                        <Td>
                            <MonospaceValue value={systemNumberB || ""} />
                        </Td>
                    </Tr>
                    {/* <Tr key="leader">
                        <Td>
                            <MonospaceValue value="Leader" />
                        </Td>
                        <Td></Td>
                        <Td></Td>
                        <Td>
                            <MonospaceValue value={data.leader} />
                        </Td>
                    </Tr> */}
                    {/* {Object.entries(data.fixed_fields)
                        .sort(([tagA], [tagB]) => tagA.localeCompare(tagB))
                        .map(([tag, value], index) => (
                            <Tr key={index}>
                                <Td>
                                    <MonospaceValue value={tag} />
                                </Td>
                                <Td></Td>
                                <Td></Td>
                                <Td>
                                    <MonospaceValue value={value} />
                                </Td>
                            </Tr>
                        ))}
                    {Object.entries(data.variable_fields)
                        .sort(([tagA], [tagB]) => tagA.localeCompare(tagB))
                        .map(([tag, fields]) =>
                            fields.map(
                                ({ ind1, ind2, subfields }, subIndex) => (
                                    <Tr key={`var-${tag}-${subIndex}`}>
                                        <Td>
                                            <MonospaceValue value={tag} />
                                        </Td>
                                        <Td>
                                            <MonospaceValue
                                                value={`${
                                                    ind1?.trim() !== ""
                                                        ? ind1
                                                        : "-"
                                                }${
                                                    ind2?.trim() !== ""
                                                        ? ind2
                                                        : "-"
                                                }`}
                                            />
                                        </Td>

                                        <Td>
                                            <Stack>
                                                {Object.entries(subfields).map(
                                                    ([key], index) => (
                                                        <StackItem key={index}>
                                                            <MonospaceValue
                                                                value={key}
                                                            />
                                                        </StackItem>
                                                    )
                                                )}
                                            </Stack>
                                        </Td>

                                        <Td>
                                            <Stack>
                                                {Object.values(subfields).map(
                                                    (values, index) =>
                                                        values.map(
                                                            (
                                                                value,
                                                                subIndex
                                                            ) => (
                                                                <StackItem
                                                                    key={`subfield-${index}-${subIndex}`}
                                                                >
                                                                    {value}
                                                                </StackItem>
                                                            )
                                                        )
                                                )}
                                            </Stack>
                                        </Td>
                                    </Tr>
                                )
                            )
                        )} */}
                </Tbody>
            )}
        </Table>
    );
};

export default MarcComparisonTable;
