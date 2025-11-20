import { Bullseye, Spinner } from "@patternfly/react-core";
import { Tbody, Td, Tr } from "@patternfly/react-table";
import type { ReactElement } from "react";

const TableLoadingBody = ({ colSpan }: { colSpan: number }): ReactElement => (
    <Tbody>
        <Tr>
            <Td colSpan={colSpan}>
                <Bullseye>
                    <Spinner size="xl" />
                </Bullseye>
            </Td>
        </Tr>
    </Tbody>
);

export default TableLoadingBody;
