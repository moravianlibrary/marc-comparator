import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useGetSystemInfo } from "../../hooks/useSystem";
import { type CollectionData } from "../../store/collection/domain";
import { selectSelectedCount } from "../../store/es/selectors";
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
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { buildSelectQuery } from "../../store/es/requests_factory";
import type { EsState } from "../../store/es/domain";
import { useLinkToAuthorities } from "../../hooks/useCatalogRecords";

interface AuthorityLinkingModalProps {
    state: EsState;
    data: CollectionData<CatalogRecord>;
    isOpen: boolean;
    onClose: () => void;
}

const AuthorityLinkingModal = ({
    state,
    data,
    isOpen,
    onClose,
}: AuthorityLinkingModalProps) => {
    const { t } = useTranslation();
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
            query: buildSelectQuery(state),
        });
        onClose();
    };

    return (
        <ConfirmModal
            isOpen={isOpen}
            onClose={onClose}
            onConfirm={handleConfirm}
            isConfirmDisabled={!base || selectedLinkers.size === 0}
            title={t("records:modals.authority-linking.title")}
            confirmLabel={t("records:actions.link-authorities")}
            cancelLabel={t("records:modals.cancel")}
            summary={
                authorityLinkers.length > 0
                    ? t("records:modals.selected-count", {
                          count: selectedItemsCount,
                      })
                    : undefined
            }
            settings={
                authorityLinkers.length > 0 ? (
                    <DescriptionList>
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                {t("records:modals.authority-linking.select-base")}
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                {isLoading ? (
                                    <Spinner size="lg" />
                                ) : (
                                    <BaseSelector
                                        availableBases={availableBases}
                                        selected={base}
                                        onChange={setBase}
                                        placeholder={t(
                                            "records:modals.authority-linking.placeholder-target-base",
                                        )}
                                    />
                                )}
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                {t("records:modals.authority-linking.select-linkers")}
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                <ToggleList
                                    options={linkerOptions}
                                    onToggle={handleLinkerToggle}
                                />
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                    </DescriptionList>
                ) : undefined
            }
        >
            {authorityLinkers.length === 0 ? (
                <Content>
                    <p>{t("records:modals.authority-linking.no-linkers")}</p>
                </Content>
            ) : (
                <p>{t("records:modals.authority-linking.description")}</p>
            )}
        </ConfirmModal>
    );
};

export default AuthorityLinkingModal;
