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
import {
    useCompareRecords,
    useGetAvailableTargetBases,
} from "../../hooks/useCatalogRecords";
import SingleSelect from "../../components/molecules/SingleSelect";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { buildSelectQuery } from "../../store/es/requests_factory";
import type { EsState } from "../../store/es/domain";

interface CompareRecordsModalProps {
    state: EsState;
    data: CollectionData<CatalogRecord>;
    isOpen: boolean;
    onClose: () => void;
}

const CompareRecordsModal = ({
    state,
    data,
    isOpen,
    onClose,
}: CompareRecordsModalProps) => {
    const { t } = useTranslation();
    const { data: availableBases, isLoading: isLoadingBases } =
        useGetAvailableTargetBases();
    const selectedItemsCount = selectSelectedCount(state, data);

    const { data: systemInfo, isLoading: isLoadingSystemInfo } =
        useGetSystemInfo();
    const comparators = systemInfo?.enabled_comparators ?? [];

    const compareRecordsMutation = useCompareRecords();

    const [targetBase, setTargetBase] = useState<string | null>(null);
    const [comparator, setComparator] = useState<string | null>(null);

    const handleConfirm = () => {
        if (!targetBase || !comparator) return;

        compareRecordsMutation.mutate({
            target_base: targetBase,
            comparator,
            query: buildSelectQuery(state),
        });
        onClose();
    };

    return (
        <ConfirmModal
            isOpen={isOpen}
            onClose={onClose}
            onConfirm={handleConfirm}
            isConfirmDisabled={!targetBase || !comparator}
            title={t("records:modals.compare.title")}
            confirmLabel={t("records:actions.run-comparisons")}
            cancelLabel={t("records:modals.cancel")}
            summary={
                availableBases?.length
                    ? t("records:modals.selected-count", {
                          count: selectedItemsCount,
                      })
                    : undefined
            }
            settings={
                availableBases?.length ? (
                    <DescriptionList>
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                {t("records:modals.compare.target-base")}
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                {isLoadingBases ? (
                                    <Spinner size="lg" />
                                ) : (
                                    <BaseSelector
                                        availableBases={availableBases}
                                        selected={targetBase}
                                        onChange={setTargetBase}
                                        placeholder={t(
                                            "records:modals.compare.placeholder-target-base",
                                        )}
                                    />
                                )}
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                {t("records:modals.compare.select-comparator")}
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                {isLoadingSystemInfo ? (
                                    <Spinner size="lg" />
                                ) : (
                                    <SingleSelect
                                        placeholder={t(
                                            "records:modals.compare.placeholder-comparator",
                                        )}
                                        options={comparators.map((comp) => ({
                                            label: comp,
                                            value: comp,
                                        }))}
                                        selected={
                                            comparator
                                                ? {
                                                      label: comparator,
                                                      value: comparator,
                                                  }
                                                : null
                                        }
                                        onChange={(option) =>
                                            setComparator(
                                                option
                                                    ? (option.value as string)
                                                    : null,
                                            )
                                        }
                                        isDisabled={availableBases.length === 0}
                                    />
                                )}
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                    </DescriptionList>
                ) : undefined
            }
        >
            {!availableBases || availableBases.length === 0 ? (
                <Content>
                    <p>{t("records:modals.compare.no-target-bases")}</p>
                </Content>
            ) : (
                <p>{t("records:modals.compare.description")}</p>
            )}
        </ConfirmModal>
    );
};

export default CompareRecordsModal;
