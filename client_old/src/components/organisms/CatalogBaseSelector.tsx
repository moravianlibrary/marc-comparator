import { type ReactElement } from "react";
import { useGetSystemInfo } from "../../hooks/useSystem";
import { DescriptionListGroup } from "@patternfly/react-core/dist/esm/components/DescriptionList/DescriptionListGroup";
import { DescriptionListTerm } from "@patternfly/react-core/dist/esm/components/DescriptionList/DescriptionListTerm";
import { DescriptionListDescription } from "@patternfly/react-core/dist/esm/components/DescriptionList/DescriptionListDescription";
import { Spinner } from "@patternfly/react-core";
import BaseSelector from "../molecules/BaseSelector";
import { useTranslation } from "react-i18next";

interface CatalogBaseSelectorProps {
    selected: string | null;
    onChange: (base: string | null) => void;
}

const CatalogBaseSelector = ({
    selected,
    onChange,
}: CatalogBaseSelectorProps): ReactElement => {
    const { t } = useTranslation("records");

    const { data: systemInfo, isLoading } = useGetSystemInfo();
    const availableBases = systemInfo?.available_bases ?? [];

    return (
        <DescriptionListGroup>
            <DescriptionListTerm>
                {t("select-base-placeholder")}
            </DescriptionListTerm>
            {isLoading ? (
                <Spinner size="lg" />
            ) : (
                <DescriptionListDescription>
                    <BaseSelector
                        availableBases={availableBases}
                        selected={selected}
                        onChange={onChange}
                        placeholder={t("select-base-placeholder")}
                    />
                </DescriptionListDescription>
            )}
        </DescriptionListGroup>
    );
};

export default CatalogBaseSelector;
