import { type Dispatch, useEffect } from "react";
import { SortingIcon } from "../../components/atoms/Icons";
import SingleSelect from "../../components/molecules/SingleSelect";
import { useGetSystemInfo } from "../../hooks/useSystem";
import type {
    CollectionAction,
    CollectionState,
} from "../../store/collection/domain";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { useTranslation } from "react-i18next";

interface RecordsTableSortByProps {
    state: CollectionState<CatalogRecord>;
    dispatch: Dispatch<CollectionAction>;
}

const RecordsTableSortBy = ({ state, dispatch }: RecordsTableSortByProps) => {
    const { t } = useTranslation();
    const { sortBy } = state;

    const { data: systemInfo } = useGetSystemInfo();
    const comparators = systemInfo?.enabled_comparators ?? [];

    const sortByOptions = [
        {
            key: "relevance",
            label: t("records:sort-by.relevance"),
            value: [
                { _score: { order: "desc" } },
                { latest_transaction: { order: "desc" } },
            ],
        },
        {
            key: "latest-sync-desc",
            label: t("records:sort-by.latest-sync-desc"),
            value: [{ latest_sync: { order: "desc" } }],
        },
        {
            key: "latest-sync-asc",
            label: t("records:sort-by.latest-sync-asc"),
            value: [{ latest_sync: { order: "asc" } }],
        },
        {
            key: "latest-transaction-desc",
            label: t("records:sort-by.latest-transaction-desc"),
            value: [{ latest_transaction: { order: "desc" } }],
        },
        {
            key: "latest-transaction-asc",
            label: t("records:sort-by.latest-transaction-asc"),
            value: [{ latest_transaction: { order: "asc" } }],
        },
        {
            key: "title-asc",
            label: t("records:sort-by.title-asc"),
            value: [{ "title.keyword": { order: "asc" } }],
        },
        {
            key: "title-desc",
            label: t("records:sort-by.title-desc"),
            value: [{ "title.keyword": { order: "desc" } }],
        },
        ...comparators.flatMap((comparator) =>
            ["desc", "asc"].map((order) => ({
                key: `score-${comparator}-${order}`,
                label: t(`records:sort-by.score-${order}`, { comparator }),
                value: [
                    {
                        [`comparisons.overall_score`]: {
                            order: order as "asc" | "desc",
                            mode: "max",
                            nested: {
                                path: "comparisons",
                                filter: {
                                    term: {
                                        "comparisons.comparator": comparator,
                                    },
                                },
                            },
                        },
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
