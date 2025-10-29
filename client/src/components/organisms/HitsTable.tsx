import { ColumnsIcon, EyeIcon, EyeSlashIcon } from "@patternfly/react-icons";
import { Table, Thead, Tr, Th, Tbody, Td } from "@patternfly/react-table";
import { Bullseye, Button } from "@patternfly/react-core";
import type { EsHit } from "../../models/api/responses/es";
import type {
    TableColumnConfig,
    TableColumnState,
} from "../../models/ui/hits_table";
import NoMatchFoundState, {
    type NoMatchFoundStateTexts,
} from "../atoms/NoMatchFoundState";
import LoadingState from "../atoms/LoadingState";
import { useState } from "react";
import { DragDropSort } from "@patternfly/react-drag-drop";

export interface HitsTableTexts {
    noMatchFound: NoMatchFoundStateTexts;
}

interface HitsTableProps<T> {
    columns: TableColumnConfig[];
    columnStates: Record<string, TableColumnState>;
    isLoading?: boolean;
    isError?: boolean;
    error?: unknown;
    hits?: Array<EsHit<T>>;
    selectedIds?: Set<string>;
    onToggleSelect: (hitId: string) => void;
    onColumnOrderChange: (columnKeys: string[]) => void;
    onColumnVisibilityToggle: (columnKey: string) => void;
    texts: HitsTableTexts;
}

const HitsTable = <T,>({
    columns,
    columnStates,
    isLoading,
    isError,
    error,
    hits,
    selectedIds,
    onToggleSelect,
    onColumnOrderChange,
    onColumnVisibilityToggle,
    texts,
}: HitsTableProps<T>) => {
    const orderedColumns = columns.sort(
        (a, b) =>
            (columnStates[a.key]?.order ?? Number.MAX_SAFE_INTEGER) -
            (columnStates[b.key]?.order ?? Number.MAX_SAFE_INTEGER)
    );
    const displayedColumns = orderedColumns.filter(
        (col) => columnStates[col.key]?.visible
    );

    const [showSettings, setShowSettings] = useState<boolean>(false);
    const header = () => (
        <Thead>
            <Tr>
                <Th>
                    <Button
                        variant="plain"
                        icon={<ColumnsIcon />}
                        hasNoPadding
                        isClicked={showSettings}
                        onClick={() => setShowSettings(!showSettings)}
                    />
                </Th>
                {displayedColumns.map((col) => (
                    <Th key={col.key}>{col.label}</Th>
                ))}
            </Tr>
        </Thead>
    );

    const renderCell = (hit: EsHit<T>, col: TableColumnConfig) => {
        if (col.render) {
            return col.render(hit._source as Partial<T>);
        }
        return String((hit._source as { [key: string]: unknown })?.[col.key]);
    };

    const loadingState = <LoadingState title="Loading results..." />;
    const errorState = (
        <div>
            <h3>Error loading results</h3>
            <pre>{String(error)}</pre>
        </div>
    );
    const noResultsState = <NoMatchFoundState texts={texts.noMatchFound} />;

    const stateBody = (stateContent: React.ReactNode) => (
        <Tbody>
            <Tr>
                <Td colSpan={displayedColumns.length + 1}>
                    <Bullseye>{stateContent}</Bullseye>
                </Td>
            </Tr>
        </Tbody>
    );

    const settingsBody = () => (
        <Tbody>
            <Tr>
                <Td colSpan={displayedColumns.length + 1}>
                    <DragDropSort
                        items={orderedColumns.map((col) => ({
                            id: col.key,
                            content: (
                                <span>
                                    <Button
                                        variant="plain"
                                        icon={
                                            columnStates[col.key]?.visible ? (
                                                <EyeIcon />
                                            ) : (
                                                <EyeSlashIcon />
                                            )
                                        }
                                        isDisabled={col.alwaysShow}
                                        onClick={() =>
                                            onColumnVisibilityToggle(col.key)
                                        }
                                    />
                                    {col.label}
                                </span>
                            ),
                        }))}
                        onDrop={(_event, items) =>
                            onColumnOrderChange(
                                items.map((item) => item.id.toString())
                            )
                        }
                    />
                </Td>
            </Tr>
        </Tbody>
    );

    const hitsBody = () => (
        <Tbody>
            {hits!.map((hit, index) => (
                <Tr key={hit._id}>
                    <Td
                        select={{
                            rowIndex: index,
                            isSelected: selectedIds?.has(hit._id) ?? false,
                            onSelect: () => onToggleSelect(hit._id),
                        }}
                    />
                    {displayedColumns.map((col) => (
                        <Td key={col.key} dataLabel={col.label}>
                            {renderCell(hit, col)}
                        </Td>
                    ))}
                </Tr>
            ))}
        </Tbody>
    );

    const tableBody = () => {
        if (showSettings) {
            return settingsBody();
        }
        if (displayedColumns.length === 0) {
            return stateBody(
                <div>No columns are visible. Please configure the columns.</div>
            );
        }
        if (isLoading) {
            return stateBody(loadingState);
        }
        if (isError) {
            return stateBody(errorState);
        }
        if (!hits || hits.length === 0) {
            return stateBody(noResultsState);
        }
        return hitsBody();
    };

    return (
        <Table isStickyHeader>
            {header()}
            {tableBody()}
        </Table>
    );
};

export default HitsTable;
