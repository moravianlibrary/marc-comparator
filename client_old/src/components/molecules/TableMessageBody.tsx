import { Bullseye, EmptyState } from "@patternfly/react-core";
import { Tbody, Td, Tr } from "@patternfly/react-table";
import type { ReactElement } from "react";

const TableMessageBody = ({
    colSpan,
    message,
}: {
    colSpan: number;
    message: string;
}): ReactElement => (
    <Tbody>
        <Tr>
            <Td colSpan={colSpan}>
                <Bullseye>
                    <EmptyState>{message}</EmptyState>
                </Bullseye>
            </Td>
        </Tr>
    </Tbody>
);

export default TableMessageBody;
