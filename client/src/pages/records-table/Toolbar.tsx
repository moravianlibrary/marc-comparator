import {
    Button,
    SearchInput,
    Toolbar,
    ToolbarContent,
    ToolbarGroup,
    ToolbarItem,
} from "@patternfly/react-core";
import type {
    CollectionAction,
    CollectionData,
    CollectionState,
} from "../../store/collection/domain";
import { useState } from "react";
import { RecordsActionsMenu } from "./RecordsActionsMenu";
import BulkSelector from "../../components/molecules/BulkSelector";
import { SortingIcon } from "../../components/atoms/Icons";
import SingleSelect from "../../components/molecules/SingleSelect";
import RecordsTableSortBy from "./SortBy";

interface RecordsTableToolbarProps {
    state: CollectionState;
    dispatch: React.Dispatch<CollectionAction>;
    data: CollectionData;
    onShowFilters: () => void;
}
const RecordsTableToolbar = ({
    state,
    dispatch,
    data,
    onShowFilters,
}: RecordsTableToolbarProps) => {
    const { config, sortBy, selectedIds, isAllSelected } = state;
    const { hits, totalItems } = data;

    const pageIds = hits?.map((hit) => hit._id) || [];

    const [searchTerm, setSearchTerm] = useState<string>("");

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
                                selectNone: "Select None",
                                selectPage: ({ count }) =>
                                    `Select Page (${count})`,
                                selectAll: ({ count }) =>
                                    `Select All (${count})`,
                                selectedCount: ({ count }) =>
                                    `${count} Selected`,
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
                            placeholder="Search records"
                            value={searchTerm}
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
                        <Button variant="control" onClick={onShowFilters}>
                            Filters
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
