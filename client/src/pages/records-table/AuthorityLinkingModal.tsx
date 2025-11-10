import { Fragment, useState } from "react";
import { useLinkToAuthorities } from "../../hooks/useAuthorityLinking";
import { useGetSystemInfo } from "../../hooks/useSystem";
import {
    type CollectionData,
    type CollectionState,
} from "../../store/collection/domain";
import {
    selectSelectedCount,
    selectSelectionQuery,
} from "../../store/collection/selectors";
import ActionsMenu from "../../components/molecules/ActionsMenu";
import ConfirmModal from "../../components/organisms/ConfirmModal";
import {
    Content,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    Spinner,
} from "@patternfly/react-core";
import BaseSelector from "../../components/molecules/BaseSelector";
import ToggleList from "../../components/molecules/ToggleList";

interface AuthorityLinkingModalProps {
    state: CollectionState;
    data: CollectionData;
    isOpen: boolean;
    onClose: () => void;
}

const AuthorityLinkingModal = ({
    state,
    data,
    isOpen,
    onClose,
}: AuthorityLinkingModalProps) => {
    const { data: systemInfo, isLoading } = useGetSystemInfo();
    const authorityLinkers = systemInfo?.enabled_authority_linkers ?? [];

    const authorityLinkingMutation = useLinkToAuthorities();

    const selectedItemsCount = selectSelectedCount(state, data);

    const [base, setBase] = useState<string | null>(null);
    const [selectedLinkers, setSelectedLinkers] = useState<Set<string>>(
        new Set()
    );

    const availableBases = authorityLinkers.flatMap(
        (linker) => linker.target_bases
    );

    const linkerOptions = authorityLinkers.map((linker) => ({
        id: linker.name,
        label: linker.name,
        isChecked: selectedLinkers.has(linker.name),
        isDisabled: !linker.target_bases.includes(base || ""),
    }));

    const handleLinkerToggle = (id: string, isChecked: boolean) => {
        setSelectedLinkers((prev) =>
            isChecked
                ? new Set(prev).add(id)
                : new Set([...prev].filter((l) => l !== id))
        );
    };

    const handleConfirm = () => {
        if (!base || selectedLinkers.size === 0) return;

        authorityLinkingMutation.mutate({
            target_base: base,
            linkers: Array.from(selectedLinkers),
            query: selectSelectionQuery(state),
        });
        onClose();
    };

    return (
        <ConfirmModal
            isOpen={isOpen}
            onClose={onClose}
            onConfirm={handleConfirm}
            isConfirmDisabled={!base || selectedLinkers.size === 0}
        >
            {authorityLinkers.length === 0 ? (
                <Content>
                    <p>No authority linkers available.</p>
                </Content>
            ) : (
                <Fragment>
                    <Content>
                        <p>Selected {selectedItemsCount} items</p>
                    </Content>
                    <DescriptionList>
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                Select base
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                {isLoading ? (
                                    <Spinner size="lg" />
                                ) : (
                                    <BaseSelector
                                        availableBases={availableBases}
                                        selected={base}
                                        onChange={setBase}
                                        placeholder="Select target base"
                                    />
                                )}
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                Select linkers
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                <ToggleList
                                    options={linkerOptions}
                                    onToggle={handleLinkerToggle}
                                />
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                    </DescriptionList>
                </Fragment>
            )}
        </ConfirmModal>
    );
};

export default AuthorityLinkingModal;
