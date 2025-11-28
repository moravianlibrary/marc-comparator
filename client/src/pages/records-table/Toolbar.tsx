import { FilterIcon } from "@patternfly/react-icons";
import {
    Button,
    SearchInput,
    Toolbar,
    ToolbarContent,
    ToolbarGroup,
    ToolbarItem,
} from "@patternfly/react-core";
import type { CollectionData } from "../../store/collection/domain";
import { useEffect, useState } from "react";
import { RecordsActionsMenu } from "./RecordsActionsMenu";
import BulkSelector from "../../components/molecules/BulkSelector";
import RecordsTableSortBy from "./SortBy";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { useTranslation } from "react-i18next";
import type { EsState, EsStateAction } from "../../store/es/domain";

interface RecordsTableToolbarProps {
    state: EsState;
    dispatch: React.Dispatch<EsStateAction>;
    data: CollectionData<CatalogRecord>;
    showFilters: boolean;
    onToggleShowFilters: () => void;
}
const RecordsTableToolbar = ({
    state,
    dispatch,
    data,
    showFilters,
    onToggleShowFilters,
}: RecordsTableToolbarProps) => {
    const { t } = useTranslation();
    const { selectedIds, isAllSelected } = state;
    const { hits, totalItems } = data;

    const pageIds = hits?.map((hit) => hit._id) || [];

    const [searchTerm, setSearchTerm] = useState<string>("");

    useEffect(() => {
        if (state.searchTerm && state.searchTerm !== searchTerm) {
            setSearchTerm(state.searchTerm);
        }
    }, [state.searchTerm]);

    const countActiveFilters =
        Object.values(state.terms || {}).reduce(
            (acc, val) => acc + (val.include?.length || 0),
            0
        ) +
        Object.keys(state.range || {}).length +
        Object.keys(state.hist || {}).length +
        Object.keys(state.dateRange || {}).length;

    return (
        <Toolbar collapseListedFiltersBreakpoint="lg">
            <ToolbarContent rowWrap={{ default: "nowrap" }}>
                <ToolbarGroup
                    key="bulk-actions"
                    align={{ default: "alignStart" }}
                >
                    <ToolbarItem>
                        <BulkSelector
                            selectedCount={
                                (isAllSelected
                                    ? totalItems
                                    : selectedIds.size) || 0
                            }
                            onPageCount={hits?.length || 0}
                            totalCount={totalItems || 0}
                            onSelectNone={() =>
                                dispatch({ type: "clearSelection" })
                            }
                            onSelectPage={() =>
                                dispatch({ type: "selectPage", pageIds })
                            }
                            onSelectAll={() => dispatch({ type: "selectAll" })}
                            texts={{
                                selectNone: t("records:selection.none"),
                                selectPage: ({ count }) =>
                                    t("records:selection.page", { count }),
                                selectAll: ({ count }) =>
                                    t("records:selection.all", { count }),
                                selectedCount: ({ count }) =>
                                    t("records:selection.selected", { count }),
                            }}
                        />
                    </ToolbarItem>
                    <ToolbarItem>
                        <RecordsActionsMenu state={state} data={data} />
                    </ToolbarItem>
                </ToolbarGroup>
                <ToolbarGroup key="search" align={{ default: "alignCenter" }}>
                    <ToolbarItem>
                        <SearchInput
                            placeholder={t("records:search.placeholder")}
                            value={state.searchTerm || searchTerm}
                            onChange={(_event, value) => setSearchTerm(value)}
                            onClear={() => {
                                setSearchTerm("");
                                dispatch({ type: "setSearchTerm", value: "" });
                            }}
                            onSearch={() =>
                                dispatch({
                                    type: "setSearchTerm",
                                    value: searchTerm,
                                })
                            }
                        />
                    </ToolbarItem>
                </ToolbarGroup>
                <ToolbarGroup key="filters" align={{ default: "alignEnd" }}>
                    <ToolbarItem>
                        <Button
                            variant="control"
                            icon={<FilterIcon />}
                            onClick={onToggleShowFilters}
                            countOptions={{
                                isRead: countActiveFilters === 0,
                                count: countActiveFilters,
                            }}
                        >
                            {showFilters
                                ? t("records:filters.hide")
                                : t("records:filters.show")}
                        </Button>
                    </ToolbarItem>
                    <ToolbarItem>
                        <RecordsTableSortBy state={state} dispatch={dispatch} />
                    </ToolbarItem>
                </ToolbarGroup>
            </ToolbarContent>
        </Toolbar>
    );
};

export default RecordsTableToolbar;
