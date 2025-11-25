import { type Dispatch, useEffect } from "react";
import { SortingIcon } from "../../components/atoms/Icons";
import SingleSelect from "../../components/molecules/SingleSelect";
import { useGetSystemInfo } from "../../hooks/useSystem";
import type {
    CollectionAction,
    CollectionState,
} from "../../store/collection/domain";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";

interface RecordsTableSortByProps {
    state: CollectionState<CatalogRecord>;
    dispatch: Dispatch<CollectionAction>;
}

const RecordsTableSortBy = ({ state, dispatch }: RecordsTableSortByProps) => {
    const { sortBy } = state;

    const { data: systemInfo } = useGetSystemInfo();
    const comparators = systemInfo?.enabled_comparators ?? [];

    const sortByOptions = [
        {
            key: "relevance",
            label: "Relevance",
            value: [
                { _score: { order: "desc" } },
                { latest_transaction: { order: "desc" } },
            ],
        },
        {
            key: "latest-sync-desc",
            label: "Latest Sync (Desc)",
            value: [{ latest_sync: { order: "desc" } }],
        },
        {
            key: "latest-sync-asc",
            label: "Latest Sync (Asc)",
            value: [{ latest_sync: { order: "asc" } }],
        },
        {
            key: "latest-transaction-desc",
            label: "Latest Transaction (Desc)",
            value: [{ latest_transaction: { order: "desc" } }],
        },
        {
            key: "latest-transaction-asc",
            label: "Latest Transaction (Asc)",
            value: [{ latest_transaction: { order: "asc" } }],
        },
        {
            key: "title-asc",
            label: "Title (A-Z)",
            value: [{ "title.keyword": { order: "asc" } }],
        },
        {
            key: "title-desc",
            label: "Title (Z-A)",
            value: [{ "title.keyword": { order: "desc" } }],
        },
        ...comparators.flatMap((comparator) =>
            ["desc", "asc"].map((order) => ({
                key: `score-${comparator}-${order}`,
                label: `Score ${comparator} (High to Low)`,
                value: [
                    {
                        field: `comparisons.${comparator}.overall_score`,
                        order: order as "asc" | "desc",
                    },
                ],
            }))
        ),
    ];

    const activeSortBy =
        (sortBy && sortByOptions.find((opt) => opt.key === sortBy.key)) ||
        sortByOptions[0];

    const handleChangeSortBy = (key: string) => {
        const selectedSortBy = sortByOptions.find((opt) => opt.key === key);
        if (selectedSortBy) {
            dispatch({ type: "setSortBy", sortBy: selectedSortBy });
        }
    };

    useEffect(() => {
        if (!sortBy || !sortByOptions.find((opt) => opt.key === sortBy.key)) {
            dispatch({ type: "setSortBy", sortBy: activeSortBy });
        }
    }, []);

    return (
        <SingleSelect
            placeholder={activeSortBy.key}
            icon={<SortingIcon />}
            options={sortByOptions.map((opt) => ({
                label: opt.label,
                value: opt.key,
            }))}
            selected={{
                label: activeSortBy.label,
                value: activeSortBy.key,
            }}
            onChange={(option) => option && handleChangeSortBy(option.value)}
            popperProps={{ position: "right" }}
        />
    );
};

export default RecordsTableSortBy;
