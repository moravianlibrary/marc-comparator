import { Td, Tr } from "@patternfly/react-table";
import MonospaceValue from "../atoms/MonospaceValue";

interface MarcFixedFieldRowProps {
    key?: string | number;
    term: string;
    value: string;
}

const MarcFixedFieldRow = ({ key, term, value }: MarcFixedFieldRowProps) => (
    <Tr key={key}>
        <Td colSpan={2}>
            <MonospaceValue value={term} />
        </Td>
        <Td>
            <MonospaceValue value={value} />
        </Td>
    </Tr>
);

export default MarcFixedFieldRow;
