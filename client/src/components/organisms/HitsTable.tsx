import { ColumnsIcon, EyeIcon, EyeSlashIcon } from "@patternfly/react-icons";
import { Table, Thead, Tr, Th, Tbody, Td } from "@patternfly/react-table";
import {
    Bullseye,
    Button,
    EmptyState,
    EmptyStateBody,
} from "@patternfly/react-core";
import type { EsHit } from "../../models/api/responses/es";
import type {
    TableColumnConfig,
    TableColumnState,
} from "../../models/ui/hits_table";
import NoMatchFoundState, {
    type NoMatchFoundStateTexts,
} from "../atoms/NoMatchFoundState";
import LoadingState from "../atoms/LoadingState";
import { useEffect, useState } from "react";
import { DragDropSort } from "@patternfly/react-drag-drop";

export interface HitsTableTexts {
    noMatchFound: NoMatchFoundStateTexts;
}

interface HitsTableProps<T> {
    columns: TableColumnConfig<EsHit<T>>[];
    columnStates: Record<string, TableColumnState>;
    isLoading?: boolean;
    isError?: boolean;
    error?: unknown;
    hits?: Array<EsHit<T>>;
    selectedIds?: Set<string>;
    onToggleSelect?: (hitId: string) => void;
    onColumnOrderChange?: (columnKeys: string[]) => void;
    onColumnVisibilityToggle?: (columnKey: string) => void;
    texts: HitsTableTexts;
}

type BodyKey =
    | "settings"
    | "no-columns"
    | "loading"
    | "error"
    | "no-results"
    | "hits";

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

    const isSimpleTable =
        !onToggleSelect || !onColumnOrderChange || !onColumnVisibilityToggle;
    const [bodyKey, setBodyKey] = useState<BodyKey>("loading");

    useEffect(() => {
        setBodyKey((prev) => {
            if (prev === "settings") return "settings";
            if (displayedColumns.length === 0) return "no-columns";
            if (isLoading) return "loading";
            if (isError) return "error";
            if (!hits || hits.length === 0) return "no-results";
            return "hits";
        });
    }, [displayedColumns.length, isLoading, isError, hits]);

    const renderCell = (hit: EsHit<T>, col: TableColumnConfig<EsHit<T>>) => {
        if (col.render) {
            return col.render(hit);
        }
        return String((hit._source as { [key: string]: unknown })?.[col.key]);
    };

    return (
        <Table isStickyHeader>
            <Thead>
                <Tr>
                    {!isSimpleTable && (
                        <Th>
                            <Button
                                variant="plain"
                                icon={<ColumnsIcon />}
                                hasNoPadding
                                isClicked={bodyKey === "settings"}
                                onClick={() =>
                                    setBodyKey(
                                        !(bodyKey === "settings")
                                            ? "settings"
                                            : "hits"
                                    )
                                }
                            />
                        </Th>
                    )}
                    {displayedColumns.map((col) => (
                        <Th key={col.key}>{col.label}</Th>
                    ))}
                </Tr>
            </Thead>
            <Tbody>
                {bodyKey !== "hits" && (
                    <Tr>
                        <Td colSpan={displayedColumns.length + 1}>
                            {bodyKey === "settings" && !isSimpleTable && (
                                <DragDropSort
                                    items={orderedColumns.map((col) => ({
                                        id: col.key,
                                        content: (
                                            <span>
                                                <Button
                                                    variant="plain"
                                                    icon={
                                                        columnStates[col.key]
                                                            ?.visible ? (
                                                            <EyeIcon />
                                                        ) : (
                                                            <EyeSlashIcon />
                                                        )
                                                    }
                                                    isDisabled={col.alwaysShow}
                                                    onClick={() =>
                                                        onColumnVisibilityToggle(
                                                            col.key
                                                        )
                                                    }
                                                />
                                                {col.label}
                                            </span>
                                        ),
                                    }))}
                                    onDrop={(_event, items) =>
                                        onColumnOrderChange(
                                            items.map((item) =>
                                                item.id.toString()
                                            )
                                        )
                                    }
                                />
                            )}
                            {bodyKey === "no-columns" && (
                                <Bullseye>
                                    <EmptyState title="No columns configured" />
                                </Bullseye>
                            )}
                            {bodyKey === "loading" && (
                                <Bullseye>
                                    <LoadingState title="Loading results..." />
                                </Bullseye>
                            )}
                            {bodyKey === "error" && (
                                <Bullseye>
                                    <EmptyState title="Error loading results">
                                        <EmptyStateBody>
                                            {String(error)}
                                        </EmptyStateBody>
                                    </EmptyState>
                                </Bullseye>
                            )}
                            {bodyKey === "no-results" && (
                                <Bullseye>
                                    <NoMatchFoundState
                                        texts={texts.noMatchFound}
                                    />
                                </Bullseye>
                            )}
                        </Td>
                    </Tr>
                )}
                {bodyKey === "hits" &&
                    hits &&
                    hits.map((hit, index) => (
                        <Tr key={hit._id}>
                            {!isSimpleTable && (
                                <Td
                                    select={{
                                        rowIndex: index,
                                        isSelected:
                                            selectedIds?.has(hit._id) ?? false,
                                        onSelect: () => onToggleSelect(hit._id),
                                    }}
                                />
                            )}
                            {displayedColumns.map((col) => (
                                <Td key={col.key} dataLabel={col.label}>
                                    {renderCell(hit, col)}
                                </Td>
                            ))}
                        </Tr>
                    ))}
            </Tbody>
        </Table>
    );
};

export default HitsTable;
