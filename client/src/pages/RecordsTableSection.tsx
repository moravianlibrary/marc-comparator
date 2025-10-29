import { type ReactElement } from "react";
import { useCatalogRecords } from "../hooks/useCatalogRecords";
import HitsTableLayout from "../components/templates/HitsTableLayout";

const RecordsTableSection = (): ReactElement => {
    const { state, dispatch, data } = useCatalogRecords();

    return (
        <HitsTableLayout
            state={state}
            dispatch={dispatch}
            data={data}
            texts={{
                hitsTable: {
                    noMatchFound: {
                        title: "No records found",
                        body: "Try adjusting your search or filter to find what you're looking for.",
                    },
                },
                pagination: {
                    perPageSuffix: "records per page",
                    ofWord: "of",
                },
                bulkSelector: {
                    selectNone: "Select none",
                    selectPage: ({ count }) => `Select page (${count})`,
                    selectAll: ({ count }) => `Select all (${count})`,
                    selectedCount: ({ count }) =>
                        `${count} record${count !== 1 ? "s" : ""} selected`,
                },
                actionsMenu: {
                    label: "Actions",
                },
                searchInput: {
                    placeholder: "Search records",
                },
                filters: {
                    showFilters: "Show filters",
                },
            }}
        />
    );
};

export default RecordsTableSection;
