import { Table, Tbody, Td, Tr } from "@patternfly/react-table";
import MonospaceValue from "../atoms/MonospaceValue";
import { Content } from "@patternfly/react-core";
import { Fragment } from "react/jsx-runtime";

interface MarcVariableFieldRowProps {
    tag: string;
    ind1: string;
    ind2: string;
    subfields: Record<string, string[]>;
    index: number;
    highlightedCodes?: string[];
    renderSubfieldDetail?: (
        code: string,
        idx: number,
        value: string
    ) => React.ReactNode;
}

const MarcVariableFieldRow = ({
    tag,
    ind1,
    ind2,
    subfields,
    index,
    highlightedCodes,
    renderSubfieldDetail,
}: MarcVariableFieldRowProps) => {
    const renderSubfieldEntry = (code: string, value: string, idx: number) => {
        const bold = highlightedCodes?.includes(code);

        const entry = (
            <Tr key={`${code}-${idx}`}>
                <Td style={{ width: "1rem" }}>
                    <MonospaceValue value={code} bold={bold} />
                </Td>
                <Td>
                    <Content>{bold ? <></> : <p>{value}</p>}</Content>
                </Td>
            </Tr>
        );

        if (renderSubfieldDetail) {
            return (
                <Fragment key={`${code}-fragment`}>
                    {entry}
                    <Tr key={`detail-${code}-${idx}`}>
                        <Td colSpan={2}>
                            {renderSubfieldDetail(code, idx, value)}
                        </Td>
                    </Tr>
                </Fragment>
            );
        }

        return entry;
    };

    return (
        <Tr key={`${tag}-${index}`}>
            <Td>
                <MonospaceValue value={tag} />
            </Td>
            <Td>
                <MonospaceValue
                    value={`${ind1?.trim() !== "" ? ind1 : "-"}${
                        ind2?.trim() !== "" ? ind2 : "-"
                    }`}
                />
            </Td>
            <Td style={{ padding: 0 }}>
                <Table variant="compact" borders={false}>
                    <Tbody>
                        {Object.entries(subfields).map(([code, values]) =>
                            values.map((value, idx) =>
                                renderSubfieldEntry(code, value, idx)
                            )
                        )}
                    </Tbody>
                </Table>
            </Td>
        </Tr>
    );
};

export default MarcVariableFieldRow;
