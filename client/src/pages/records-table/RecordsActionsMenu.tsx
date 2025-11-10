import { Fragment, useState } from "react";
import {
    type CollectionData,
    type CollectionState,
} from "../../store/collection/domain";
import {
    selectSelectedCount,
    selectSelectionQuery,
} from "../../store/collection/selectors";
import ActionsMenu from "../../components/molecules/ActionsMenu";
import AuthorityLinkingModal from "./AuthorityLinkingModal";
import CompareRecordsModal from "./CompareRecordsModal";
import ValidateRecordsModal from "./ValidateRecordsModal";
import ConfirmModal from "../../components/organisms/ConfirmModal";
import {
    useReindexRecords,
    useSetHiddenStateOfRecords,
} from "../../hooks/useCatalogRecords";

interface RecordsActionsMenuProps {
    state: CollectionState;
    data: CollectionData;
}

export const RecordsActionsMenu = ({
    state,
    data,
}: RecordsActionsMenuProps) => {
    const [visibleModal, setVisibleModal] = useState<
        "link" | "compare" | "validate" | "hide" | "unhide" | "reindex" | null
    >(null);

    const config = [
        {
            label: "Link Records to Authorities",
            onClick: () => setVisibleModal("link"),
        },
        {
            label: "Run Comparisons",
            onClick: () => setVisibleModal("compare"),
        },
        {
            label: "Run Validations",
            onClick: () => setVisibleModal("validate"),
        },
        {
            label: "Hide Records",
            onClick: () => setVisibleModal("hide"),
        },
        {
            label: "Unhide Records",
            onClick: () => setVisibleModal("unhide"),
        },
        {
            label: "Reindex Records",
            onClick: () => setVisibleModal("reindex"),
        },
    ];

    const setHiddenStateOfRecordsMutation = useSetHiddenStateOfRecords();
    const reindexRecordsMutation = useReindexRecords();

    const selectedItemsCount = selectSelectedCount(state, data);
    const selectionQuery = selectSelectionQuery(state);

    const handleHideConfirm = () => {
        setHiddenStateOfRecordsMutation.mutate({
            query: selectionQuery,
            hide: true,
        });
        setVisibleModal(null);
    };

    const handleUnhideConfirm = () => {
        setHiddenStateOfRecordsMutation.mutate({
            query: selectionQuery,
            hide: false,
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
                label="Records Actions"
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
                isOpen={visibleModal === "unhide"}
                onClose={() => setVisibleModal(null)}
                onConfirm={handleUnhideConfirm}
            >
                Are you sure you want to unhide {selectedItemsCount} selected
                records?
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
