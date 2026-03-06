import { Fragment, useState } from "react";
import { type CollectionData } from "../../store/collection/domain";
import { selectSelectedCount } from "../../store/es/selectors";
import ActionsMenu from "../../components/molecules/ActionsMenu";
import AuthorityLinkingModal from "./AuthorityLinkingModal";
import CompareRecordsModal from "./CompareRecordsModal";
import ValidateRecordsModal from "./ValidateRecordsModal";
import ConfirmModal from "../../components/organisms/ConfirmModal";
import {
    useProcessRecords,
    useReindexRecords,
    useSetRecordsVisibility,
} from "../../hooks/useCatalogRecords";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { buildSelectQuery } from "../../store/es/requests_factory";
import { useTranslation } from "react-i18next";
import type { EsState } from "../../store/es/domain";

interface RecordsActionsMenuProps {
    state: EsState;
    data: CollectionData<CatalogRecord>;
}

export const RecordsActionsMenu = ({
    state,
    data,
}: RecordsActionsMenuProps) => {
    const { t } = useTranslation();
    const [visibleModal, setVisibleModal] = useState<
        | "process"
        | "link"
        | "compare"
        | "validate"
        | "hide"
        | "make-visible"
        | "reindex"
        | null
    >(null);

    const setRecordsVisibilityMutation = useSetRecordsVisibility();
    const reindexRecordsMutation = useReindexRecords();
    const processRecordsMutation = useProcessRecords();

    const selectedItemsCount = selectSelectedCount(state, data);
    const selectionQuery = buildSelectQuery(state);
    const hasSelection = selectedItemsCount > 0;

    const handleProcess = () => {
        if (!hasSelection) return;
        setVisibleModal("process");
    };

    const handleProcessConfirm = () => {
        processRecordsMutation.mutate(selectionQuery);
        setVisibleModal(null);
    };

    const config = [
        { label: t("records:actions.link-authorities"), onClick: () => setVisibleModal("link") },
        { label: t("records:actions.run-comparisons"), onClick: () => setVisibleModal("compare") },
        { label: t("records:actions.run-validations"), onClick: () => setVisibleModal("validate") },
        { label: t("records:actions.hide-records"), onClick: () => setVisibleModal("hide") },
        { label: t("records:actions.make-records-visible"), onClick: () => setVisibleModal("make-visible") },
        { label: t("records:actions.reindex-records"), onClick: () => setVisibleModal("reindex") },
    ];

    const mainAction = {
        label: t("records:actions.process-selected"),
        onClick: handleProcess,
    };

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
                disabled={!hasSelection}
                mainAction={mainAction}
                label={t("records:actions.more-actions")}
                dropdownSectionLabel={t("records:actions.advanced-actions")}
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
                title={t("records:modals.hide.title")}
                confirmLabel={t("records:modals.hide.confirm")}
                cancelLabel={t("records:modals.cancel")}
                summary={t("records:modals.selected-count", { count: selectedItemsCount })}
            >
                <p>{t("records:modals.hide.body")}</p>
            </ConfirmModal>
            <ConfirmModal
                isOpen={visibleModal === "make-visible"}
                onClose={() => setVisibleModal(null)}
                onConfirm={handleMakeVisibleConfirm}
                title={t("records:modals.make-visible.title")}
                confirmLabel={t("records:modals.make-visible.confirm")}
                cancelLabel={t("records:modals.cancel")}
                summary={t("records:modals.selected-count", { count: selectedItemsCount })}
            >
                <p>{t("records:modals.make-visible.body")}</p>
            </ConfirmModal>
            <ConfirmModal
                isOpen={visibleModal === "process"}
                onClose={() => setVisibleModal(null)}
                onConfirm={handleProcessConfirm}
                title={t("records:modals.process.title")}
                confirmLabel={t("records:modals.process.confirm")}
                cancelLabel={t("records:modals.cancel")}
                summary={t("records:modals.selected-count", { count: selectedItemsCount })}
            >
                {t("records:modals.process.body")}
            </ConfirmModal>
            <ConfirmModal
                isOpen={visibleModal === "reindex"}
                onClose={() => setVisibleModal(null)}
                onConfirm={handleReindexConfirm}
                title={t("records:modals.reindex.title")}
                confirmLabel={t("records:modals.reindex.confirm")}
                cancelLabel={t("records:modals.cancel")}
                summary={t("records:modals.selected-count", { count: selectedItemsCount })}
            >
                <p>{t("records:modals.reindex.body")}</p>
            </ConfirmModal>
        </Fragment>
    );
};

export default RecordsActionsMenu;
