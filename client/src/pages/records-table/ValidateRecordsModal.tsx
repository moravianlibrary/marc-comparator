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
} from "@patternfly/react-core";
import ToggleList from "../../components/molecules/ToggleList";
import type { CatalogRecord } from "../../models/api/responses/catalog_record";
import { buildSelectQuery } from "../../store/es/requests_factory";
import type { EsState } from "../../store/es/domain";
import { useValidateRecords } from "../../hooks/useCatalogRecords";

interface ValidateRecordsModalProps {
    state: EsState;
    data: CollectionData<CatalogRecord>;
    isOpen: boolean;
    onClose: () => void;
}

const ValidateRecordsModal = ({
    state,
    data,
    isOpen,
    onClose,
}: ValidateRecordsModalProps) => {
    const { t } = useTranslation();
    const { data: systemInfo, isLoading } = useGetSystemInfo();
    const validators = systemInfo?.enabled_validators ?? [];

    const validateRecordsMutation = useValidateRecords();

    const selectedItemsCount = selectSelectedCount(state, data);

    const [selectedValidators, setSelectedValidators] = useState<Set<string>>(
        new Set()
    );

    const validatorOptions = validators.map((validator) => ({
        id: validator,
        label: validator,
        isChecked: selectedValidators.has(validator),
    }));

    const handleValidatorToggle = (id: string, isChecked: boolean) => {
        setSelectedValidators((prev) =>
            isChecked
                ? new Set(prev).add(id)
                : new Set([...prev].filter((l) => l !== id))
        );
    };

    const handleConfirm = () => {
        if (selectedValidators.size === 0) return;

        validateRecordsMutation.mutate({
            validators: Array.from(selectedValidators),
            query: buildSelectQuery(state),
        });
        onClose();
    };

    return (
        <ConfirmModal
            isOpen={isOpen}
            onClose={onClose}
            onConfirm={handleConfirm}
            isConfirmDisabled={selectedValidators.size === 0}
            title={t("records:modals.validate.title")}
            confirmLabel={t("records:actions.run-validations")}
            cancelLabel={t("records:modals.cancel")}
            summary={
                validators.length > 0
                    ? t("records:modals.selected-count", {
                          count: selectedItemsCount,
                      })
                    : undefined
            }
            settings={
                validators.length > 0 ? (
                    <DescriptionList>
                        <DescriptionListGroup>
                            <DescriptionListTerm>
                                {t("records:modals.validate.select-validators")}
                            </DescriptionListTerm>
                            <DescriptionListDescription>
                                <ToggleList
                                    options={validatorOptions}
                                    onToggle={handleValidatorToggle}
                                />
                            </DescriptionListDescription>
                        </DescriptionListGroup>
                    </DescriptionList>
                ) : undefined
            }
        >
            {validators.length === 0 ? (
                <Content>
                    <p>{t("records:modals.validate.no-validators")}</p>
                </Content>
            ) : (
                <p>{t("records:modals.validate.description")}</p>
            )}
        </ConfirmModal>
    );
};

export default ValidateRecordsModal;
