import { type Dispatch, type ReactElement } from "react";
import { SortingIcon } from "../../components/atoms/Icons";
import SingleSelect from "../../components/molecules/SingleSelect";
import { useTranslation } from "react-i18next";
import type { EsState, EsStateAction } from "../../store/es/domain";

interface RecordsTableSortByProps {
    state: EsState;
    dispatch: Dispatch<EsStateAction>;
}

const RecordsTableSortBy = ({
    state,
    dispatch,
}: RecordsTableSortByProps): ReactElement | null => {
    const { t } = useTranslation("records");
    const { sortBy } = state;

    if (!sortBy) return null;

    const sortByOptions = [
        "relevance",
        "latest-sync-desc",
        "latest-sync-asc",
        "latest-transaction-desc",
        "latest-transaction-asc",
        "title-asc",
        "title-desc",
        "score-intiim-desc",
        "score-intiim-asc",
    ];

    return (
        <SingleSelect
            placeholder={t(`sort-by.${sortBy}`)}
            icon={<SortingIcon />}
            options={sortByOptions.map((opt) => ({
                label: t(`sort-by.${opt}`),
                value: opt,
            }))}
            selected={{
                label: t(`sort-by.${sortBy}`),
                value: sortBy,
            }}
            onChange={(option) =>
                option && dispatch({ type: "setSortBy", sortBy: option.value })
            }
            popperProps={{ position: "right" }}
        />
    );
};

export default RecordsTableSortBy;
