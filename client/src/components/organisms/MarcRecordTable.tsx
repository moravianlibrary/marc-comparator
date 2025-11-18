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

interface MarcRecordTableProps {
    base?: string;
    systemNumber?: string;
    noDataMessage?: string;
}

const MarcRecordTable = ({
    base,
    systemNumber,
    noDataMessage = "No data available",
}: MarcRecordTableProps): ReactElement => {
    const { data, isLoading } = useGetMarcRecord(
        base || "",
        systemNumber || "",
        !!base && !!systemNumber
    );

    return (
        <Table variant="compact">
            {isLoading ? (
                <Tbody>
                    <Tr>
                        <Td colSpan={4}>
                            <Bullseye>
                                <Spinner size="xl" />
                            </Bullseye>
                        </Td>
                    </Tr>
                </Tbody>
            ) : !data ? (
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
                    <Tr key="id">
                        <Td>
                            <MonospaceValue value="System Number" />
                        </Td>
                        <Td></Td>
                        <Td></Td>
                        <Td>
                            <MonospaceValue value={systemNumber || ""} />
                        </Td>
                    </Tr>
                    <Tr key="leader">
                        <Td>
                            <MonospaceValue value="Leader" />
                        </Td>
                        <Td></Td>
                        <Td></Td>
                        <Td>
                            <MonospaceValue value={data.leader} />
                        </Td>
                    </Tr>
                    {Object.entries(data.fixed_fields)
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
                        )}
                </Tbody>
            )}
        </Table>
    );
};

export default MarcRecordTable;
