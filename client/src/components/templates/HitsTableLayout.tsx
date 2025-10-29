import { Fragment } from "react/jsx-runtime";
import {
    Button,
    Pagination,
    SearchInput,
    Toolbar,
    ToolbarContent,
    ToolbarGroup,
    ToolbarItem,
} from "@patternfly/react-core";
import HitsTable, { type HitsTableTexts } from "../organisms/HitsTable";
import type { StaticUiText } from "../../models/ui/text";
import type {
    CollectionAction,
    CollectionData,
    CollectionState,
} from "../../store/collection/domain";
import {
    InnerScrollContainer,
    OuterScrollContainer,
} from "@patternfly/react-table";
import BulkSelector, {
    type BulkSelectorTexts,
} from "../molecules/BulkSelector";
import ActionsMenu, { type ActionsMenuTexts } from "../molecules/ActionsMenu";
import { useState } from "react";
import SingleSelect from "../molecules/SingleSelect";
import { SortingIcon } from "../atoms/Icons";

interface PaginationTexts {
    perPageSuffix: StaticUiText;
    ofWord: StaticUiText;
}

interface SearchInputTexts {
    placeholder: StaticUiText;
}

interface FiltersTexts {
    showFilters: StaticUiText;
}

export interface HitsTableLayoutTexts {
    hitsTable: HitsTableTexts;
    pagination: PaginationTexts;
    bulkSelector: BulkSelectorTexts;
    actionsMenu: ActionsMenuTexts;
    searchInput: SearchInputTexts;
    filters: FiltersTexts;
}

interface EsTableComplexFiltersProps {
    state: CollectionState;
    dispatch: React.Dispatch<CollectionAction>;
    data: CollectionData;
    texts: HitsTableLayoutTexts;
}

const HitsTableLayout = ({
    state,
    dispatch,
    data,
    texts,
}: EsTableComplexFiltersProps) => {
    const {
        config,
        columnStates,
        page,
        perPage,
        sortBy,
        selectedIds,
        isAllSelected,
    } = state;
    const { columns, perPage: perPageOptions } = config;
    const { isLoading, isError, error, hits, totalItems } = data;

    const pageIds = hits?.map((hit) => hit._id) || [];

    const bulkSelector = (
        <BulkSelector
            selectedCount={(isAllSelected ? totalItems : selectedIds.size) || 0}
            onPageCount={hits?.length || 0}
            totalCount={totalItems || 0}
            onSelectNone={() => dispatch({ type: "clearSelection" })}
            onSelectPage={() => dispatch({ type: "selectPage", pageIds })}
            onSelectAll={() => dispatch({ type: "selectAll" })}
            texts={texts.bulkSelector!}
        />
    );

    const actionsMenu = (
        <ActionsMenu
            config={config.actions}
            disabled={!isAllSelected && selectedIds?.size === 0}
            texts={texts.actionsMenu}
        />
    );

    const bulkActionsControls = (
        <ToolbarGroup key="bulk-actions" align={{ default: "alignStart" }}>
            <ToolbarItem>{bulkSelector}</ToolbarItem>
            <ToolbarItem>{actionsMenu}</ToolbarItem>
        </ToolbarGroup>
    );

    const [searchTerm, setSearchTerm] = useState<string>("");
    const searchBar = (
        <SearchInput
            placeholder={texts.searchInput.placeholder}
            value={searchTerm}
            onChange={(_event, value) => setSearchTerm(value)}
            onClear={() => {
                setSearchTerm("");
                dispatch({ type: "setSearchTerm", value: "" });
            }}
            onSearch={() =>
                dispatch({ type: "setSearchTerm", value: searchTerm })
            }
        />
    );

    const searchControls = (
        <ToolbarGroup key="search" align={{ default: "alignCenter" }}>
            <ToolbarItem>{searchBar}</ToolbarItem>
        </ToolbarGroup>
    );

    const showFiltersButton = (
        <Button variant="control">{texts.filters.showFilters}</Button>
    );

    const sorting = (
        <SingleSelect
            icon={<SortingIcon />}
            options={config.sortBy.map((sortOption) => sortOption.label)}
            selected={sortBy.label}
            onSelect={(label) =>
                dispatch({
                    type: "setSortBy",
                    sortBy: config.sortBy.find((o) => o.label === label)!,
                })
            }
        />
    );

    const filterControls = (
        <ToolbarGroup key="filters" align={{ default: "alignEnd" }}>
            <ToolbarItem>{showFiltersButton}</ToolbarItem>
            <ToolbarItem>{sorting}</ToolbarItem>
        </ToolbarGroup>
    );

    const controls = (
        <Toolbar collapseListedFiltersBreakpoint="lg">
            <ToolbarContent rowWrap={{ default: "nowrap" }}>
                {bulkActionsControls}
                {searchControls}
                {filterControls}
            </ToolbarContent>
        </Toolbar>
    );

    const table = (
        <HitsTable
            columns={columns}
            columnStates={columnStates}
            isLoading={isLoading}
            isError={isError}
            error={error}
            hits={hits}
            selectedIds={isAllSelected ? new Set(pageIds) : selectedIds}
            onToggleSelect={(id) =>
                dispatch({ type: "toggleSelection", id, pageIds })
            }
            onColumnOrderChange={(columnKeys) =>
                dispatch({ type: "setColumnOrder", columnKeys })
            }
            onColumnVisibilityToggle={(columnKey) =>
                dispatch({ type: "toggleColumnVisibility", columnKey })
            }
            texts={texts.hitsTable}
        />
    );

    const handlePaginationChange = (newPage: number, newPerPage?: number) => {
        dispatch({
            type: "setPaginationParams",
            page: newPage,
            perPage: newPerPage || perPage || 0,
        });
    };

    const pagination = (
        <Pagination
            style={{ marginLeft: 20, marginRight: 20 }}
            perPageOptions={perPageOptions.options.map((o) => ({
                value: o,
                title: o.toString(),
            }))}
            itemCount={totalItems}
            page={page}
            perPage={perPage}
            onSetPage={(_event, newPage, newPerPage) =>
                handlePaginationChange(newPage, newPerPage)
            }
            onPerPageSelect={(_event, newPerPage, newPage) =>
                handlePaginationChange(newPage, newPerPage)
            }
            variant="bottom"
            titles={{
                perPageSuffix: texts.pagination.perPageSuffix,
                ofWord: texts.pagination.ofWord,
            }}
        />
    );

    return (
        <Fragment>
            <OuterScrollContainer
                style={{
                    marginLeft: 20,
                    marginRight: 20,
                    marginTop: 10,
                    marginBottom: 10,
                }}
            >
                {controls}
                <InnerScrollContainer>{table}</InnerScrollContainer>
                {pagination}
            </OuterScrollContainer>
        </Fragment>
    );
};

export default HitsTableLayout;
