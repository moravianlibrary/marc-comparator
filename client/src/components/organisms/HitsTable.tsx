import { ColumnsIcon, EyeIcon, EyeSlashIcon } from "@patternfly/react-icons";
import { Table, Thead, Tr, Th, Tbody, Td } from "@patternfly/react-table";
import {
    Bullseye,
    Button,
    EmptyState,
    EmptyStateBody,
} from "@patternfly/react-core";
import type { EsHit } from "../../models/api/responses/es";
import NoMatchFoundState, {
    type NoMatchFoundStateTexts,
} from "../atoms/NoMatchFoundState";
import LoadingState from "../atoms/LoadingState";
import { useEffect, useState, type Dispatch } from "react";
import { DragDropSort } from "@patternfly/react-drag-drop";
import type { EsState, EsStateAction } from "../../store/es/domain";

export interface HitsTableTexts {
    noMatchFound: NoMatchFoundStateTexts;
}

interface HitsTableProps<T> {
    state: EsState;
    dispatch: Dispatch<EsStateAction>;
    variant?: "simple" | "default";
    isLoading?: boolean;
    isError?: boolean;
    error?: unknown;
    hits?: Array<EsHit<T>>;
    getColumnLabel?: (columnKey: string) => string | null;
    renderColumnHeader?: (columnKey: string) => React.ReactNode | null;
    renderCell?: (columnKey: string, hit: EsHit<T>) => React.ReactNode | null;
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
    state,
    dispatch,
    variant = "default",
    isLoading,
    isError,
    error,
    hits,
    getColumnLabel,
    renderColumnHeader,
    renderCell,
    texts,
}: HitsTableProps<T>) => {
    const [bodyKey, setBodyKey] = useState<BodyKey>("loading");

    const columns = Object.entries(state.columns)
        .sort(([, a], [, b]) => a.order - b.order)
        .map(([key, colState]) => ({
            key,
            visible: colState.visible,
        }));
    const visibleColumns = columns
        .filter(({ visible }) => visible)
        .map(({ key }) => key);
    const columnLabels = columns.reduce((acc, { key }) => {
        acc[key] = getColumnLabel ? getColumnLabel(key) || key : key;
        return acc;
    }, {} as Record<string, string>);

    useEffect(() => {
        setBodyKey((prev) => {
            if (prev === "settings") return "settings";
            if (visibleColumns.length === 0) return "no-columns";
            if (isLoading) return "loading";
            if (isError) return "error";
            if (!hits || hits.length === 0) return "no-results";
            return "hits";
        });
    }, [visibleColumns, isLoading, isError, hits]);

    const handleRenderColumnHeader = (columnKey: string) => {
        const node = renderColumnHeader && renderColumnHeader(columnKey);
        return node ? node : columnLabels[columnKey] || columnKey;
    };

    const handleRenderCell = (columnKey: string, hit: EsHit<T>) => {
        return (
            (renderCell && renderCell(columnKey, hit)) ||
            String((hit._source as { [key: string]: unknown })?.[columnKey])
        );
    };

    return (
        <Table isStickyHeader>
            <Thead>
                <Tr>
                    {variant !== "simple" && (
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
                    {visibleColumns.map((key) => (
                        <Th key={key}>{handleRenderColumnHeader(key)}</Th>
                    ))}
                </Tr>
            </Thead>
            <Tbody>
                {bodyKey !== "hits" && (
                    <Tr>
                        <Td colSpan={visibleColumns.length + 1}>
                            {bodyKey === "settings" && variant !== "simple" && (
                                <DragDropSort
                                    items={columns.map(({ key, visible }) => ({
                                        id: key,
                                        content: (
                                            <span>
                                                <Button
                                                    variant="plain"
                                                    icon={
                                                        visible ? (
                                                            <EyeIcon />
                                                        ) : (
                                                            <EyeSlashIcon />
                                                        )
                                                    }
                                                    onClick={() =>
                                                        dispatch({
                                                            type: "toggleColumnVisibility",
                                                            columnKey: key,
                                                        })
                                                    }
                                                />
                                                {columnLabels[key] || key}
                                            </span>
                                        ),
                                    }))}
                                    onDrop={(_event, items) =>
                                        dispatch({
                                            type: "setColumnOrder",
                                            columnKeys: items.map((item) =>
                                                item.id.toString()
                                            ),
                                        })
                                    }
                                />
                            )}
                            {bodyKey === "no-columns" && (
                                <EmptyState
                                    title="No columns configured"
                                    isFullHeight
                                    height="300px"
                                    style={{
                                        height: "300px",
                                        width: "100%",
                                    }}
                                />
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
                            {variant !== "simple" && (
                                <Td
                                    select={{
                                        rowIndex: index,
                                        isSelected:
                                            (state.isAllSelected ||
                                                state.selectedIds.has(
                                                    hit._id
                                                )) ??
                                            false,
                                        onSelect: () =>
                                            dispatch({
                                                type: "toggleSelection",
                                                id: hit._id,
                                                pageIds: hits.map((h) => h._id),
                                            }),
                                    }}
                                />
                            )}
                            {visibleColumns.map((key) => (
                                <Td key={key} dataLabel={columnLabels[key]}>
                                    {handleRenderCell(key, hit)}
                                </Td>
                            ))}
                        </Tr>
                    ))}
            </Tbody>
        </Table>
    );
};

export default HitsTable;
