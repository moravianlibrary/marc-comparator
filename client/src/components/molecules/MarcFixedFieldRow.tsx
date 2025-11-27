import { Td, Tr } from "@patternfly/react-table";
import MonospaceValue from "../atoms/MonospaceValue";

interface MarcFixedFieldRowProps {
    term: string;
    value: string;
    renderFieldDetail?: (
        tag: string,
        fieldIdx: number
    ) => React.ReactNode | null;
}

const MarcFixedFieldRow = ({
    term,
    value,
    renderFieldDetail,
}: MarcFixedFieldRowProps) => {
    const content = (
        <Tr>
            <Td colSpan={2}>
                <MonospaceValue value={term} />
            </Td>
            <Td colSpan={2}>
                <MonospaceValue value={value} />
            </Td>
        </Tr>
    );

    const detailContent = renderFieldDetail ? renderFieldDetail(term, 0) : null;

    if (!detailContent) return content;

    return (
        <>
            {content}
            <Tr>
                <Td colSpan={4} style={{ padding: 0 }}>
                    {detailContent}
                </Td>
            </Tr>
        </>
    );
};

export default MarcFixedFieldRow;
