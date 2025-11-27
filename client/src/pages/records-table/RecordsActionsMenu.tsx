import { Fragment, useState } from "react";
import {
    type CollectionData,
    type CollectionState,
} from "../../store/collection/domain";
import { selectSelectedCount } from "../../store/collection/selectors";
import ActionsMenu from "../../components/molecules/ActionsMenu";
import AuthorityLinkingModal from "./AuthorityLinkingModal";
import CompareRecordsModal from "./CompareRecordsModal";
import ValidateRecordsModal from "./ValidateRecordsModal";
import ConfirmModal from "../../components/organisms/ConfirmModal";
import {
    useReindexRecords,
    useSetRecordsVisibility,
} from "../../hooks/useCatalogRecords";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { buildSelectQuery } from "../../store/collection/requests_factory";
import { useTranslation } from "react-i18next";

interface RecordsActionsMenuProps {
    state: CollectionState<CatalogRecord>;
    data: CollectionData<CatalogRecord>;
}

export const RecordsActionsMenu = ({
    state,
    data,
}: RecordsActionsMenuProps) => {
    const { t } = useTranslation();
    const [visibleModal, setVisibleModal] = useState<
        | "link"
        | "compare"
        | "validate"
        | "hide"
        | "make-visible"
        | "reindex"
        | null
    >(null);

    const config = [
        {
            label: t("records:actions.link-authorities"),
            onClick: () => setVisibleModal("link"),
        },
        {
            label: t("records:actions.run-comparisons"),
            onClick: () => setVisibleModal("compare"),
        },
        {
            label: t("records:actions.run-validations"),
            onClick: () => setVisibleModal("validate"),
        },
        {
            label: t("records:actions.hide-records"),
            onClick: () => setVisibleModal("hide"),
        },
        {
            label: t("records:actions.make-records-visible"),
            onClick: () => setVisibleModal("make-visible"),
        },
        {
            label: t("records:actions.reindex-records"),
            onClick: () => setVisibleModal("reindex"),
        },
    ];

    const setRecordsVisibilityMutation = useSetRecordsVisibility();
    const reindexRecordsMutation = useReindexRecords();

    const selectedItemsCount = selectSelectedCount(state, data);
    const selectionQuery = buildSelectQuery(state);

    const handleHideConfirm = () => {
        setRecordsVisibilityMutation.mutate({
            query: selectionQuery,
            visible: false,
        });
        setVisibleModal(null);
    };

    const handleMakeVisibleConfirm = () => {
        setRecordsVisibilityMutation.mutate({
            query: selectionQuery,
            visible: true,
        });
        setVisibleModal(null);
    };

    const handleReindexConfirm = () => {
        reindexRecordsMutation.mutate(selectionQuery);
        setVisibleModal(null);
    };

    return (
        <Fragment>
            <ActionsMenu
                config={config}
                disabled={selectSelectedCount(state, data) === 0}
                label={t("records:actions.label")}
            />
            <AuthorityLinkingModal
                state={state}
                data={data}
                isOpen={visibleModal === "link"}
                onClose={() => setVisibleModal(null)}
            />
            <CompareRecordsModal
                state={state}
                data={data}
                isOpen={visibleModal === "compare"}
                onClose={() => setVisibleModal(null)}
            />
            <ValidateRecordsModal
                state={state}
                data={data}
                isOpen={visibleModal === "validate"}
                onClose={() => setVisibleModal(null)}
            />
            <ConfirmModal
                isOpen={visibleModal === "hide"}
                onClose={() => setVisibleModal(null)}
                onConfirm={handleHideConfirm}
            >
                Are you sure you want to hide {selectedItemsCount} selected
                records?
            </ConfirmModal>
            <ConfirmModal
                isOpen={visibleModal === "make-visible"}
                onClose={() => setVisibleModal(null)}
                onConfirm={handleMakeVisibleConfirm}
            >
                Are you sure you want to make {selectedItemsCount} selected
                records visible?
            </ConfirmModal>
            <ConfirmModal
                isOpen={visibleModal === "reindex"}
                onClose={() => setVisibleModal(null)}
                onConfirm={handleReindexConfirm}
            >
                Are you sure you want to reindex {selectedItemsCount} selected
                records?
            </ConfirmModal>
        </Fragment>
    );
};

export default RecordsActionsMenu;
